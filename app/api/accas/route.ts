import { NextResponse } from "next/server";

export async function POST() {
  const runtimeUri = process.env.CODEWORDS_RUNTIME_URI;
  const apiKey = process.env.CODEWORDS_API_KEY;
  
  try {
    const res = await fetch(`${runtimeUri}/run/dailybet_api_5159157b`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ tz: "UTC" }),
    });
    
    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: err }, { status: res.status });
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

