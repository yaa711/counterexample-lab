export async function request<T>(path: string, data?: unknown): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method: data === undefined ? "GET" : "POST",
    headers:
      data === undefined ? undefined : { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
    signal: AbortSignal.timeout(90000),
  });
  const value = await response.json();
  if (!response.ok)
    throw new Error(value.error ?? `Request failed (${response.status})`);
  return value as T;
}

export function download(name: string, value: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "The request did not complete. Check that the local server is running.";
}
