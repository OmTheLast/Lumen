export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/health") {
      return Response.json({
        ok: true,
        service: "lumen",
        target: "lumen.ompatnaik.com",
        runtime: "cloudflare-workers",
      });
    }

    if (url.pathname === "/download") {
      const assetRequest = new Request(new URL("/install.sh", request.url), {
        headers: request.headers,
        method: "GET",
      });
      const asset = await env.ASSETS.fetch(assetRequest);

      if (!asset.ok) {
        return new Response("Lumen installer unavailable.", { status: 404 });
      }

      const headers = new Headers(asset.headers);
      headers.set("Content-Type", "text/x-shellscript; charset=utf-8");
      headers.set("Content-Disposition", 'attachment; filename="lumen-installer.sh"');
      headers.set("Cache-Control", "public, max-age=0, must-revalidate");

      return new Response(request.method === "HEAD" ? null : asset.body, {
        status: asset.status,
        statusText: asset.statusText,
        headers,
      });
    }

    return env.ASSETS.fetch(request);
  },
};
