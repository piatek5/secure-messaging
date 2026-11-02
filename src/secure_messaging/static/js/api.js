export async function api(method, path, body) {
    const options = { method, headers: {} };
    if (body !== undefined) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body)
    }
    const response = await fetch(path, options);
    const data = response.status === 204 ? null : await response.json();
    return { ok: response.ok, status: response.status, data };
}
