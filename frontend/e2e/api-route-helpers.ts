// Playwright URL matchers for backend REST APIs.
// Avoid broad globs containing "/api/" in the middle — they match Vite paths like /src/api/*.ts
// and return JSON mocks instead of JavaScript modules.
export function isRestApiUrl(url: URL): boolean {
  return url.pathname.startsWith('/api/')
}
