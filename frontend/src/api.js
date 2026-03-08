// Automatically grabs the current IP of your NAS from your browser's address bar
const BASE_URL = `http://${window.location.hostname}:8000`;

// This is your global helper for all backend calls [cite: 2026-03-05]
export async function authorizedFetch(endpoint, options = {}) {
  const token = localStorage.getItem('token'); // Grab the passport from storage [cite: 2026-03-05]
  
  // Prepare the headers with the Authorization "Bearer" token [cite: 2026-03-05, 2026-03-08]
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const response = await fetch(`http://127.0.0.1:8000${endpoint}`, {
    ...options,
    headers,
  });

  // If the server says the token is expired or invalid (401) [cite: 2026-03-05, 2026-03-08]
  if (response.status === 401) {
    console.warn("Session expired. Logging out...");
    localStorage.clear();
    window.location.reload(); // This triggers the App.vue gatekeeper to show Login [cite: 2026-03-05]
  }

  return response;
}