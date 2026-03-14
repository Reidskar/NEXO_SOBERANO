import { serve } from "https://deno.land/std@0.177.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.7.1"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // 1. Consultar evidencias de las últimas 24h
    const hace24h = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
    const { data: recentdocs, error: fetchError } = await supabaseClient
      .from('nexo_documentos')
      .select('content, metadata')
      .gte('created_at', hace24h)

    if (fetchError) throw fetchError

    if (!recentdocs || recentdocs.length === 0) {
      return new Response(JSON.stringify({ ok: true, message: 'No hay nueva inteligencia para resumir' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    // 2. Generar Resumen con LLM (Gemini Pro)
    // Simulado para el paquete base
    const summary = `
      # NEXO SOBERANO | GLOBAL BRIEFING
      Resumen de las últimas 24h generado en el Edge.
      Hallazgos en Geopolítica: ${recentdocs.length} documentos analizados.
    `

    // 3. Guardar Reporte en Storage
    const reportPath = `reports/daily/${new Date().toISOString().split('T')[0]}.md`
    await supabaseClient.storage.from('nexo-media').upload(reportPath, summary, { contentType: 'text/markdown', upsert: true })

    // 4. Notificar a Discord (Opcional)
    const discordWebhook = Deno.env.get('DISCORD_WEBHOOK_URL')
    if (discordWebhook) {
      await fetch(discordWebhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: summary.substring(0, 2000) }),
      })
    }

    return new Response(JSON.stringify({ ok: true, report_path: reportPath }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    })
  }
})
