export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

export const hexToUint8Array = (hex: string) => {
  return new Uint8Array(hex.match(/.{1,2}/g)!.map((val) => parseInt(val, 16)))
}
