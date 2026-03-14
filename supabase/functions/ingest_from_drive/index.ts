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

    const url = new URL(req.url)
    const { pathname } = url

    // 1. OAuth Callback Handler
    if (pathname.endsWith('/callback')) {
      const code = url.searchParams.get('code')
      if (!code) throw new Error('No se recibió código de Google')

      // Intercambiar código por tokens
      const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          code,
          client_id: Deno.env.get('GOOGLE_OAUTH_CLIENT_ID') ?? '',
          client_secret: Deno.env.get('GOOGLE_OAUTH_CLIENT_SECRET') ?? '',
          redirect_uri: `${url.origin}${pathname}`,
          grant_type: 'authorization_code',
        }),
      })

      const tokens = await tokenResponse.json()
      if (tokens.error) throw new Error(`Google Error: ${tokens.error_description}`)

      // Guardar refresh_token de forma segura (idealmente encriptado)
      const { error: dbError } = await supabaseClient
        .from('oauth_credentials')
        .upsert({
          provider: 'google_drive',
          refresh_token: tokens.refresh_token,
          access_token: tokens.access_token,
          expires_at: new Date(Date.now() + tokens.expires_in * 1000).toISOString(),
          updated_at: new Date().toISOString(),
        })

      if (dbError) throw dbError

      return new Response(JSON.stringify({ ok: true, message: 'OAuth completado exitosamente' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      })
    }

    // 2. Poll/Sync Trigger
    const { action } = await req.json()
    if (action === 'sync') {
      // Lógica de sincronización proactiva:
      // - Obtener refresh_token del DB
      // - Listar archivos nuevos en Drive
      // - Descargar y subir a nexo-media Bucket
      // - Insertar en public.evidencia
      return new Response(JSON.stringify({ ok: true, status: 'Sync iniciado' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    return new Response(JSON.stringify({ error: 'Ruta no encontrada' }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 404,
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    })
  }
})
