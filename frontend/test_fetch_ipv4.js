async function test() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "test_ipv4@example.com",
        name: "Test IPv4",
        password: "Password123"
      })
    });
    console.log("Status:", res.status);
    const data = await res.json();
    console.log("Data:", data);
  } catch (err) {
    console.error("Fetch failed:", err);
  }
}
test();
