import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [text, setText] = useState("");
  const [translation, setTranslation] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("Marathi");
  const [isTranslating, setIsTranslating] = useState(false);
  const [error, setError] = useState("");

  // Gmail related states
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [emails, setEmails] = useState([]);
  const [emailContent, setEmailContent] = useState(null);
  const [showEmailList, setShowEmailList] = useState(false);

  // Check authentication status on load
  useEffect(() => {
    checkAuthStatus();

    // Check URL parameters for auth callback
    const queryParams = new URLSearchParams(window.location.search);
    const authStatus = queryParams.get("auth");

    if (authStatus === "success") {
      checkAuthStatus();
      // Clean URL
      window.history.replaceState({}, document.title, "/");
    }
  }, []);

  // Check if user is authenticated with Gmail
  const checkAuthStatus = async () => {
    try {
      const response = await axios.get(
        "http://127.0.0.1:8000/gmail/check-auth"
      );
      setIsAuthenticated(response.data.success);
    } catch (error) {
      console.error("Error checking auth status:", error);
    }
  };

  // Handle Gmail login
  const handleGmailLogin = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get("http://127.0.0.1:8000/gmail/auth-url");
      // Redirect to Google auth page
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error("Error getting auth URL:", error);
      setError("Failed to connect to Gmail. Please try again later.");
      setIsLoading(false);
    }
  };

  // Fetch recent emails
  const fetchRecentEmails = async () => {
    if (!isAuthenticated) {
      setError("Please login with Gmail first");
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.get(
        "http://127.0.0.1:8000/gmail/recent-emails"
      );
      setEmails(response.data.emails);
      setShowEmailList(true);
      setIsLoading(false);
    } catch (error) {
      // If backend returned a 401 with an auth_url, redirect user to authenticate
      if (
        error.response &&
        error.response.status === 401 &&
        error.response.data &&
        error.response.data.detail &&
        error.response.data.detail.auth_url
      ) {
        window.location.href = error.response.data.detail.auth_url;
        return;
      }
      console.error("Error fetching emails:", error);
      setError("Failed to fetch emails. Please try again.");
      setIsLoading(false);
    }
  };

  // Fetch and display email content
  const handleEmailSelect = async (messageId) => {
    setIsLoading(true);

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/gmail/email-content",
        {
          message_id: messageId,
        }
      );
      setEmailContent(response.data.email);
      setText(response.data.email.body);
      setShowEmailList(false);
      setIsLoading(false);
    } catch (error) {
      if (
        error.response &&
        error.response.status === 401 &&
        error.response.data &&
        error.response.data.detail &&
        error.response.data.detail.auth_url
      ) {
        window.location.href = error.response.data.detail.auth_url;
        return;
      }
      console.error("Error fetching email content:", error);
      setError("Failed to load email content.");
      setIsLoading(false);
    }
  };

  // Translate email content
  const handleTranslateEmail = async (messageId) => {
    setIsTranslating(true);

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/gmail/translate-email",
        {
          message_id: messageId,
          language: selectedLanguage,
        }
      );
      setEmailContent(response.data.original_email);
      setTranslation(response.data.translated_body);
      setShowEmailList(false);
      setIsTranslating(false);
    } catch (error) {
      if (
        error.response &&
        error.response.status === 401 &&
        error.response.data &&
        error.response.data.detail &&
        error.response.data.detail.auth_url
      ) {
        window.location.href = error.response.data.detail.auth_url;
        return;
      }
      console.error("Error translating email:", error);
      setError("Failed to translate email content.");
      setIsTranslating(false);
    }
  };

  const handleTranslate = async () => {
    if (!text.trim()) {
      setError("Please enter some text to translate");
      return;
    }

    setError("");
    setIsTranslating(true);

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/translate-to-marathi",
        {
          text: text,
          language: selectedLanguage,
        }
      );
      setTranslation(
        response.data.translation || response.data.marathi_translation
      );
      setIsTranslating(false);
    } catch (error) {
      console.error("Error translating:", error);
      setError(
        "Translation failed. Please check if the backend server is running."
      );
      setIsTranslating(false);
    }
  };

  return (
    <div className="app-container">
      <div className="app-header">
        <h1>📧 MailSathi</h1>
        <p className="tagline">Mail Translator</p>

        {/* Gmail Login Button */}
        <div className="gmail-auth-section">
          {isAuthenticated ? (
            <button
              className="gmail-button connected"
              onClick={fetchRecentEmails}
              disabled={isLoading}
            >
              {isLoading ? "Loading..." : "View My Emails"}
            </button>
          ) : (
            <button
              className="gmail-button"
              onClick={handleGmailLogin}
              disabled={isLoading}
            >
              {isLoading ? "Connecting..." : "Connect Gmail Account"}
            </button>
          )}
        </div>
      </div>

      {/* Email List */}
      {showEmailList && (
        <div className="email-list-container">
          <h2>Recent Emails</h2>
          {emails.length > 0 ? (
            <div className="email-list">
              {emails.map((email) => (
                <div
                  key={email.id}
                  className="email-item"
                  onClick={() => handleEmailSelect(email.id)}
                >
                  <div className="email-header">
                    <span className="email-from">{email.from}</span>
                    <span className="email-date">{email.date}</span>
                  </div>
                  <div className="email-subject">{email.subject}</div>
                  <div className="email-snippet">{email.snippet}</div>
                  <div className="email-actions">
                    <button
                      className="email-action-btn view"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEmailSelect(email.id);
                      }}
                    >
                      View
                    </button>
                    <button
                      className="email-action-btn translate"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTranslateEmail(email.id);
                      }}
                    >
                      Translate
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p>No emails found.</p>
          )}
          <button
            className="back-button"
            onClick={() => setShowEmailList(false)}
          >
            Back to Translation
          </button>
        </div>
      )}

      {/* Email Content and Translation */}
      {!showEmailList && (
        <div className="translation-container">
          <div className="input-section">
            <h2>{emailContent ? "Email Content" : "Enter Text"}</h2>
            {emailContent && (
              <div className="email-content-header">
                <p>
                  <strong>From:</strong> {emailContent.from}
                </p>
                <p>
                  <strong>Subject:</strong> {emailContent.subject}
                </p>
                <p>
                  <strong>Date:</strong> {emailContent.date}
                </p>
              </div>
            )}
            <textarea
              className="text-area"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Type or paste English text here..."
              rows="6"
            />
            <div style={{ marginTop: "0.75rem", textAlign: "left" }}>
              <label style={{ fontSize: "0.9rem", marginRight: "0.5rem" }}>
                Translate to:
              </label>
              <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                style={{ padding: "6px 8px", borderRadius: "6px" }}
              >
                <option>Marathi</option>
                <option>Hindi</option>
                <option>Tamil</option>
                <option>Kannada</option>
                <option>Telugu</option>
                <option>Bengali</option>
                <option>English</option>
              </select>
            </div>
            {error && <div className="error-message">{error}</div>}
            <div className="button-group">
              {isAuthenticated && (
                <button
                  className="email-button"
                  onClick={fetchRecentEmails}
                  disabled={isTranslating || isLoading}
                >
                  View My Emails
                </button>
              )}
              <button
                className="translate-button"
                onClick={handleTranslate}
                disabled={isTranslating}
              >
                {isTranslating
                  ? "Translating..."
                  : `Translate to ${selectedLanguage}`}
              </button>
            </div>
          </div>

          <div className="output-section">
            <h2>{selectedLanguage} Translation</h2>
            <div className="translation-result">
              {isTranslating ? (
                <div className="loading-spinner">
                  <div className="spinner"></div>
                  <p>Translating your text...</p>
                </div>
              ) : translation ? (
                <p>{translation}</p>
              ) : (
                <p className="placeholder-text">
                  Your translation will appear here...
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      <footer className="app-footer">
        <p>Powered by Ollama LLaMA3 | MailSathi &copy; 2025</p>
      </footer>
    </div>
  );
}

export default App;
