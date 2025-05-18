import React, { useState } from "react";
import './App.css';





function FactCheck() {
  const [videoURL, setVideoUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const dummyResult = {
    "Topic #1": {
      theme: "COVID-19 Vaccines",
      claims: [
        {
          id: 1,
          text: "The Covid-19 Vaccines cause autism.",
          verdict: "False",
          explanation: "Not true lol",
          links: [
            "cdc.gov"
          ]
        }
      ]
    },
    "Topic #2": {
      theme: "American Airlines Explosions",
      claims: [
        {
          id: 1,
          text: "30 airplanes exploded in 2011",
          verdict: "False",
          explanation: "It was 31",
          links: [
            "youtube.com",
            "gmail.com"
          ]
        },
        {
          id: 2,
          text: "Airplanes are cool",
          verdict: "True",
          explanation: "I agree",
          links: [
            "youtube.com",
            "gmail.com"
          ]
        }
      ]
    }
  }

  const useDummy = true;


  const handleSubmit = async (e) => {
    e.preventDefault()
    if (useDummy){
      setResult(dummyResult);
      setLoading(false)
      return;
    }
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
      <form onSubmit={handleSubmit} className="search">
        <input
          class="search-input"
          type="text"
          placeholder="Enter a social media video URL"
          value={videoURL}
          onChange={(e) => setVideoUrl(e.target.value)}
        />
      </form>

      {result && (
        <div>
        <ul>
          { Object.entries(result).map(([key, topic], i) => (
            <li key={i} className="topic">
              <h2> {topic.theme} </h2>
              <ul>
                {topic.claims.map((claim, j) => (
                  <li key={j} className="claim">
                    <p><strong>Claim:</strong> {claim.text}</p>
                    <p><strong>Verdict:</strong> {claim.verdict}</p>
                    <p><strong>Explanation:</strong> {claim.explanation}</p>
                    <p className="links">
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