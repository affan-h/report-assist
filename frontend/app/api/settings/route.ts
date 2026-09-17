import { NextResponse } from "next/server";

const FASTAPI_URL =
  process.env.NEXT_PUBLIC_FASTAPI_BACKEND_URL || "http://0.0.0.0:8000";

export async function GET() {
  try {
    const res = await fetch(`${FASTAPI_URL}/api/v1/process/config/settings`); // Adjust endpoint
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch config" },
      { status: 500 }
    );
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${FASTAPI_URL}/api/v1/process/config/settings`, {
      // Adjust endpoint
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to save config" },
      { status: 500 }
    );
  }
}
