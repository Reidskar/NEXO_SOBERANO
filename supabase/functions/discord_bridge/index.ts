import { serve } from "https://deno.land/std@0.177.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.7.1"
import nacl from "https://esm.sh/tweetnacl@1.0.3"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const signature = req.headers.get('x-signature-ed25519')
    const timestamp = req.headers.get('x-signature-timestamp')
    const body = await req.text()

    // 1. Verificar firma de Discord (Seguridad)
    const PUBLIC_KEY = Deno.env.get('DISCORD_PUBLIC_KEY') ?? ''
    const isVerified = nacl.sign.detached.verify(
      new TextEncoder().encode(timestamp + body),
      hexToUint8Array(signature ?? ''),
      hexToUint8Array(PUBLIC_KEY)
    )

    if (!isVerified) {
      return new Response('invalid request signature', { status: 401 })
    }

    const payload = JSON.parse(body)

    // 2. Ping/Pong (Discord Initialization)
    if (payload.type === 1) {
      return new Response(JSON.stringify({ type: 1 }), { headers: { 'Content-Type': 'application/json' } })
    }

    // 3. Manejar Comandos (Slash Commands)
    if (payload.type === 2) {
      const { name } = payload.data

      if (name === 'evidencia') {
        const id = payload.data.options[0].value
        return new Response(JSON.stringify({
          type: 4,
          data: { content: `🔍 Buscando evidencia con ID: ${id}... (Link firmado en desarrollo)` }
        }), { headers: { 'Content-Type': 'application/json' } })
      }

      if (name === 'resumen') {
        return new Response(JSON.stringify({
          type: 4,
          data: { content: `🗞️ Generando resumen diario de NEXO...` }
        }), { headers: { 'Content-Type': 'application/json' } })
      }
    }

    return new Response(JSON.stringify({ error: 'Comando no reconocido' }), { status: 400 })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), { status: 400 })
  }
})

function hexToUint8Array(hex: string) {
  if (!hex) return new Uint8Array(0);
  const match = hex.match(/.{1,2}/g);
  if (!match) return new Uint8Array(0);
  return new Uint8Array(match.map((val) => parseInt(val, 16)));
}
