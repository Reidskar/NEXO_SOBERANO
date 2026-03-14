import { createClient } from "https://esm.sh/@supabase/supabase-js@2.7.1"

export const getSupabaseClient = (serviceRole = false) => {
  return createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    serviceRole 
      ? Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '' 
      : Deno.env.get('SUPABASE_ANON_KEY') ?? ''
  )
}
