import { serve } from "https://deno.land/std@0.177.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0"

// Mock Polymarket Data for the initial scan
const getPolymarketScan = () => {
  return [
    { country: "Venezuela", question: "¿Habrá cambio de régimen en Venezuela antes de fin de año?", probability: 0.12, type: "polymarket" },
    { country: "Argentina", question: "¿La inflación mensual caerá por debajo del 1%?", probability: 0.85, type: "polymarket" },
    { country: "Chile", question: "¿Se aprobará una nueva ola de reformas constitucionales / protestas masivas?", probability: 0.38, type: "polymarket" }
  ];
};

const getGeminiSentiment = async (apiKey: string, country: string) => {
  // Simplified direct REST call
  const prompt = `Actúa como un psicólogo de masas experto en Gustave Le Bon y praxeología austríaca.
Calcula un 'heat_score' de 0 a 1 midiendo el nivel de deshumanización y riesgo de estallido en ${country}.
Responde SOLO con un JSON en este formato {"heat_score": 0.xx}`;
  
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
  });
  
  if (!resp.ok) {
    console.error(`Gemini Error: ${resp.status}`);
    return 0.5;
  }
  
  const data = await resp.json();
  const rawText = data.candidates?.[0]?.content?.parts?.[0]?.text || '{"heat_score": 0.5}';
  try {
     const match = rawText.match(/\{[^]*\}/);
     if (match) {
        const parsed = JSON.parse(match[0]);
        return parsed.heat_score || 0.5;
     }
  } catch(e) {}
  return 0.5;
};

serve(async (req) => {
  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const geminiKey = Deno.env.get('GEMINI_API_KEY')!;
    
    const supabase = createClient(supabaseUrl, supabaseKey);
    
    const marketData = getPolymarketScan();
    let savedCount = 0;
    
    for (const item of marketData) {
       // Insert Polymarket
       await supabase.from("conflict_indicators").insert({
          country: item.country,
          indicator_type: "polymarket",
          score: item.probability,
          metadata: { question: item.question }
       });
       savedCount++;
       
       // Calculate Sentiment
       const heat = await getGeminiSentiment(geminiKey, item.country);
       await supabase.from("conflict_indicators").insert({
          country: item.country,
          indicator_type: "sentiment",
          score: heat,
          metadata: { reason: "Gemini Analysis" }
       });
       savedCount++;
    }

    return new Response(
      JSON.stringify({ ok: true, message: `Market Observer ejecutado con éxito. ${savedCount} registros guardados.` }),
      { headers: { "Content-Type": "application/json" } },
    )
  } catch (error) {
    console.error("Error en function market_observer:", error)
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    })
  }
})
