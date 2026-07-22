import { cookies } from "next/headers";
import { NextResponse } from "next/server";

// Server-side only — reads httpOnly access_token cookie and returns it to the client.
// Never exposed to other origins; used only by our own socket init flow.
export async function GET() {
  const token = (await cookies()).get("access_token")?.value;
  if (!token) return NextResponse.json({ token: null }, { status: 401 });
  return NextResponse.json({ token });
}
