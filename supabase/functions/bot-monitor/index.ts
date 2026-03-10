import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

serve(async (req) => {
  const BOT_HEALTH_URL = Deno.env.get("BOT_HEALTH_URL") || "http://your-bot-server:8000/health"
  
  try {
    const res = await fetch(BOT_HEALTH_URL, { signal: AbortSignal.timeout(5000) })
    const data = await res.json()
    
    return new Response(
      JSON.stringify({ status: "ok", bot: data }),
      { headers: { "Content-Type": "application/json" } },
    )
  } catch (err) {
    return new Response(
      JSON.stringify({ status: "error", message: "Bot unreachable", details: err.message }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    )
  }
})
