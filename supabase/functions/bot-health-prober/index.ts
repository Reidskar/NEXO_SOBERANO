import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req: Request) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
  )
  
  const BOT_HEALTH_URL = Deno.env.get("BOT_HEALTH_URL") || "http://nexo-discord-bot:3000/health"
  const ALERT_RELAY_URL = Deno.env.get("ALERT_RELAY_URL") || "http://nexo-webhook-relay:4000/alerts"
  
  const logAlert = async (title: string, text: string, level: string) => {
    // 1. Log to DB
    await supabase.from('alerts').insert({
      level,
      source: 'supabase-prober',
      title,
      body: text,
      meta: { bot_url: BOT_HEALTH_URL }
    })
    
    // 2. Forward to Relay (Webhooks)
    try {
      await fetch(ALERT_RELAY_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'health', source: 'supabase-prober', title, text, level })
      })
    } catch (e) {
      console.error("Relay unreachable:", e)
    }
  }

  try {
    const res = await fetch(BOT_HEALTH_URL, { 
      signal: AbortSignal.timeout(5000) 
    })
    
    if (res.status !== 200) {
      await logAlert('Bot Unhealthy', `Health check failed with status ${res.status}`, 'warning')
    }
    
    return new Response(JSON.stringify({ ok: res.ok, status: res.status }), { 
      headers: { "Content-Type": "application/json" } 
    })
  } catch (err: unknown) {
    const errorMessage = err instanceof Error ? err.message : String(err);
    await logAlert('Bot Unreachable', errorMessage, 'critical')

    return new Response(JSON.stringify({ ok: false, error: errorMessage }), { 
      status: 502, 
      headers: { "Content-Type": "application/json" } 
    })
  }
})
