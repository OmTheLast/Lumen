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

    return env.ASSETS.fetch(request);
  },
};
