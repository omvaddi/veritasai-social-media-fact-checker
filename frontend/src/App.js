import React, { useState } from "react";
import './App.css';


function FactCheck() {
  const [videoURL, setVideoUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)
  
  const handleSubmit = async (e) => {
    setResult(null);
    setError(null);
    setMessage(null)
    setLoading(true)

    e.preventDefault()

    const response = await fetch("http://localhost:5000/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ video_url: videoURL }),
    });

    const json = await response.json();

    if(!response.ok){
      setError(json.error || "Unknown error occured");
      setLoading(false)
      return;
    }

    if(json.message === "No verifiable claims found."){
      setMessage(json.message);
      setLoading(false)
      return;
    }

    setResult(json)
    setLoading(false)
  }

  return (
    <div style = {{ padding: "2rem", fontFamily: 'Lexend'}} >
      <h1>Veritas</h1>
      
      <div style={{ display: "flex", justifyContent: "center", marginTop: "2rem"}}>
        <form onSubmit={handleSubmit} className="search">
          <input
            className="search-input"
            type="text"
            placeholder="Enter a social media video URL"
            value={videoURL}
            onChange={(e) => setVideoUrl(e.target.value)}
          />
        </form>
      </div>

      {loading && (
        <div className="loading-container">
          <p>Analyzing video, please wait...</p>
          <div className="loading"></div>
          <div className="loading"></div>
          <div className="loading"></div>
          <div className="loading"></div>
          <div className="loading"></div>
        </div>
      )}

      {error && (
        <div className = "error">
          {error}
        </div>
      )}

      {message && (
        <div className="message">
          {message}
        </div>
      )}

      {result && (
        <div className="results">   
          { Object.entries(result).map(([key, topic], i) => (
            <div className="topic-card" key={i}>
              <h2> {topic.theme} </h2>
                {topic.claims.map((claim, j) => (
                  <details key={j} className="claim">
                    <summary className={claim.verdict} style={{ cursor: "pointer"}}>
                      {claim.verdict == "True" && "✅ "}
                      {claim.verdict == "False" && "❌ "}
                      {claim.verdict == "Likely True" && "🤔 "}
                      {claim.verdict == "Likely False" && "⚠️ "}
                      {claim.verdict == "Insufficient Evidence" && "❓ "}
                      {claim.text}
                    </summary>
                    <p><strong>Verdict:</strong> {claim.verdict}</p>
                    <p><strong>Explanation:</strong> {claim.explanation}</p>
                    <p className="links">
                      {claim.links.map((link, k) => (
                          <a 
                            key={k}
                            href={link}
                            target="_blank"
                            rel = "noopener noreferrer"
                            className = "link-badge"
                            title={link}
                          >
                            {link}
                          </a>
                      ))}
                    </p>
                  </details>
                ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default FactCheck;