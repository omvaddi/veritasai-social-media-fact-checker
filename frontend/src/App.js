import React, { useState } from "react";
import './App.css';


function FactCheck() {
  const [videoURL, setVideoUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null)

  const dummyResult = {
    "Topic #1": {
        "theme": "Definitions of womanhood and gender participation in sports",
        "claims": [
            {
                "id": 1,
                "text": "A woman is somebody that can have a baby under certain circumstances.",
                "query": "Can all women have babies under certain circumstances?",
                "verdict": "Unclear",
                "explanation": "There is no relevant evidence provided in these search results directly addressing or defining what a 'woman' is, nor whether the ability to have a baby is central to that definition. The snippets refer to topics such as breastfeeding, Medicaid benefits for pregnant women, and women's health rights, but none provide clear or direct support or contradiction for the claim that a woman is defined as somebody who can have a baby under certain circumstances.",
                "links": [
                    "https://www.cdc.gov/breastfeeding-special-circumstances/hcp/exposures/lead.html",
                    "https://www.pa.gov/services/dhs/apply-for-medicaid-benefits.html",
                    "https://www.dol.gov/general/topic/health-plans/cobra"
                ]
            },
            {
                "id": 2,
                "text": "Men are able to play in women's sports in some cases.",
                "query": "Are men able to compete in women's sports in some situations?",
                "verdict": "Likely True",
                "explanation": "There is evidence that, in certain cases, men (specifically transgender women, who were assigned male at birth but identify and compete as women) have been allowed to compete in women's sports. The snippet from 'Keeping Men Out of Women's Sports \u2013 The White House' directly states that 'athletic associations have allowed men to compete in women's sports.' The SF.gov article gives historical examples, citing 'many examples over the last several decades of transwomen competing in sports,' and names Renee Richards, a trans woman who competed in women's tennis. However, some of the most recent policies, such as the NCAA policy described, are making such participation more restrictive. Overall, there is clear evidence that in some circumstances, men (including trans women) have been able to participate in women's sports.",
                "links": [
                    "https://www.whitehouse.gov/presidential-actions/2025/02/keeping-men-out-of-womens-sports/",
                    "https://www.sf.gov/trans-women-in-sports-facts-over-fear",
                    "https://www.espn.com/espn/story/_/id/38209262/transgender-athlete-laws-state-legislation-science"
                ]
            }
        ]
    }
}

  const useDummy = false;
  const dummyLoading = false;

  
  

  const handleSubmit = async (e) => {
    
    setResult(null);
    setError(null);


    e.preventDefault()
    if (useDummy){
      setResult(dummyResult);
      setLoading(false)
      return;
    }
    if (dummyLoading){
      setLoading(true)
      return;
    }

    setLoading(true)

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