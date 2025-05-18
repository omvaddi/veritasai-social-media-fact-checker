import React, { useState } from "react";


function FactCheck() {
  const [videoURL, setVideoUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);


  const handleSubmit = async () => {
    setLoading(true);
    setResult(null)
    const response = await fetch("http://localhost:5000/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ video_url: videoURL }),
    });

    const json = await response.json();
    setResult(json)
    setLoading(false)
  }

  return (
    <div style = {{ padding: "2rem", fontFamily: "Arial"}} >
      <h1>Social Media Video Fact Checker</h1>
      <input
        type="text"
        placeholder="Enter a social media video URL"
        value={videoURL}
        onChange={(e) => setVideoUrl(e.target.value)}
        style={{ width: "50%", padding: "1rem", marginRight: "1rem"}}
      />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Checking..." : "Check Video"}
      </button>

      {result && (
        <div>
        <ul>
          { Object.entries(result).map(([key, topic], index) => (
            <li>
              <h2> {topic.theme} </h2>
              <ul>
                {topic.claims.map((claim, i) => (
                  <li>
                    <p><strong>Claim:</strong> {claim.text}</p>
                    <p><strong>Verdict:</strong> {claim.verdict}</p>
                    <p><strong>Explanation:</strong> {claim.explanation}</p>
                    <p>
                      <strong>Links: </strong>
                      {claim.links.map((link, j) => (
                        <a key={j} href={link} target="_blank" rel = "noopener noreferrer">
                        [{ link }]
                        </a>
                      ))}
                    </p>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
        </div>
      )
    }

    </div>
  )
}

export default FactCheck;