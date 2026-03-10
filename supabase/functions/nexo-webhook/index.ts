import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const SUPABASE_URL = Deno.env.get('SUPABASE_URL') ?? ''
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''

serve(async (req) => {
  const { method } = req
  
  if (method === 'OPTIONS') {
    return new Response('ok', { headers: { 'Access-Control-Allow-Origin': '*' } })
  }

  try {
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    const payload = await req.json()
    
    // Payload esperado: { tenant_slug: '...', type: '...', title: '...', body: '...' }
    const { tenant_slug, type, title, body, data } = payload
    
    if (!tenant_slug) throw new Error("Missing tenant_slug")

    const schema = `tenant_${tenant_slug.toLowerCase().replace('-', '_')}`
    
    // Insertar en la tabla alertas del esquema del tenant
    const { error } = await supabase
      .schema(schema)
      .from('alertas')
      .insert({
        tipo: type || 'webhook',
        titulo: title || 'Nueva Alerta Externa',
        descripcion: body || '',
        datos_raw: data || {},
        fuente: 'external_webhook'
      })

    if (error) throw error

    return new Response(JSON.stringify({ status: 'ok', schema }), {
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    })
  }
})
