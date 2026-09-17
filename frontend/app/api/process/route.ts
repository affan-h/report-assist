const FASTAPI_URL =
  process.env.NEXT_PUBLIC_FASTAPI_BACKEND_URL || "http://0.0.0.0:8000";

export async function POST(req: Request) {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ detail: "Method Not Allowed" }), {
      status: 405,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const formData = await req.formData();
    const prompt = formData.get("prompt");
    const session_id = formData.get("session_id");
    const analyze_only = formData.get("analyze_only");
    const files = formData.getAll("files") as File[];

    if (!prompt) {
      return new Response(JSON.stringify({ detail: "Prompt is missing" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const backendFormData = new FormData();
    backendFormData.append("prompt", prompt);
    if (session_id) backendFormData.append("session_id", session_id);
    if (analyze_only) backendFormData.append("analyze_only", analyze_only);

    if (files && files.length > 0) {
      files.forEach((file) => {
        backendFormData.append("files", file);
      });
    }

    const backendResponse = await fetch(`${FASTAPI_URL}/api/v1/process`, {
      method: "POST",
      body: backendFormData,
    });

    if (!backendResponse.ok) {
      const errorBody = await backendResponse.text();
      console.error("FastAPI backend error:", errorBody);
      return new Response(
        JSON.stringify({ detail: "Backend server error", error: errorBody }),
        {
          status: backendResponse.status,
          headers: { "Content-Type": "multipart/form-data" },
        }
      );
    }

    // 5. Send the FastAPI response (which contains the session_id) back to the frontend
    const responseData = await backendResponse.json();
    return new Response(JSON.stringify(responseData), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error in /api/process:", error);
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    return new Response(
      JSON.stringify({ detail: "Internal Server Error", error: errorMessage }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
