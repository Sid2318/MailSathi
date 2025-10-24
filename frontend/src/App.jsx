import React, { useState, useEffect } from "react";
import axios from "axios";
// import "./App.css";

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

  // Helper function to clean email content
  const cleanEmailContent = (content) => {
    if (!content) return "";
    return content
      .replace(
        /View web version:[\s\S]*?(?:\*{3,}[\s\S]*?(?:\n|$)|(?:\n|$))/g,
        ""
      )
      .trim();
  };

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

      // If audio was generated successfully, automatically start playing it
      if (response.data.audio_ready) {
        try {
          await axios.post("http://127.0.0.1:8000/tts/speak-email", {
            email: response.data.original_email,
            translated_body: response.data.translated_body,
            language: selectedLanguage,
          });
        } catch (error) {
          console.error("Error starting audio playback:", error);
        }
      }
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
      const cleanedText = cleanEmailContent(text);
      const response = await axios.post(
        "http://127.0.0.1:8000/translate-to-marathi",
        {
          text: cleanedText,
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
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-indigo-600 mb-2">
            📧 MailSathi
          </h1>
          <p className="text-lg text-gray-600">Mail Translator</p>

          {/* Gmail Login Button */}
          <div className="mt-6">
            {isAuthenticated ? (
              <button
                className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={fetchRecentEmails}
                disabled={isLoading}
              >
                {isLoading ? "Loading..." : "View My Emails"}
              </button>
            ) : (
              <button
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-6 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleGmailLogin}
                disabled={isLoading}
              >
                {isLoading ? "Connecting..." : "Connect Gmail Account"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Email List */}
      {showEmailList && (
        <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-6">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800">
            Recent Emails
          </h2>
          {emails.length > 0 ? (
            <div className="space-y-4">
              {emails.map((email) => (
                <div
                  key={email.id}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow duration-200 cursor-pointer"
                  onClick={() => handleEmailSelect(email.id)}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-semibold text-gray-800">
                      {email.from}
                    </span>
                    <span className="text-sm text-gray-500">{email.date}</span>
                  </div>
                  <div className="text-gray-700 font-medium mb-2">
                    {email.subject}
                  </div>
                  <div className="text-gray-600 text-sm mb-3">
                    {email.snippet}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      className="px-4 py-2 bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-md text-sm font-medium transition-colors duration-200"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEmailSelect(email.id);
                      }}
                    >
                      View
                    </button>
                    <button
                      className="px-4 py-2 bg-indigo-600 text-white hover:bg-indigo-700 rounded-md text-sm font-medium transition-colors duration-200"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTranslateEmail(email.id);
                      }}
                    >
                      Translate
                    </button>
                    {translation && (
                      <>
                        <button
                          className="px-4 py-2 flex items-center gap-1 bg-green-600 text-white hover:bg-green-700 rounded-md text-sm font-medium transition-colors duration-200"
                          onClick={async (e) => {
                            e.stopPropagation();
                            try {
                              const response = await axios.post(
                                "http://127.0.0.1:8000/tts/speak-email",
                                {
                                  email: emailContent,
                                  translated_body: translation,
                                  language: selectedLanguage,
                                }
                              );
                              if (!response.data.success) {
                                setError(
                                  response.data.message ||
                                    "Failed to play audio"
                                );
                              }
                            } catch (error) {
                              console.error("Error playing audio:", error);
                              setError(
                                "Failed to play audio. Please try again."
                              );
                            }
                          }}
                        >
                          <span>🔊</span>
                          <span>Listen</span>
                        </button>
                        <button
                          className="px-4 py-2 flex items-center gap-1 bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-md text-sm font-medium transition-colors duration-200"
                          onClick={async (e) => {
                            e.stopPropagation();
                            try {
                              await axios.post(
                                "http://127.0.0.1:8000/tts/stop"
                              );
                            } catch (error) {
                              console.error("Error stopping audio:", error);
                            }
                          }}
                        >
                          ⏹️ Stop
                        </button>
                      </>
                    )}
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
        <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-2xl font-semibold mb-4 text-gray-800">
              {emailContent ? "Email Content" : "Enter Text"}
            </h2>
            {emailContent && (
              <div className="mb-4 text-sm text-gray-700 space-y-2">
                <p className="flex gap-2">
                  <strong className="text-gray-900">From:</strong>{" "}
                  {emailContent.from}
                </p>
                <p className="flex gap-2">
                  <strong className="text-gray-900">Subject:</strong>{" "}
                  {emailContent.subject}
                </p>
                <p className="flex gap-2">
                  <strong className="text-gray-900">Date:</strong>{" "}
                  {emailContent.date}
                </p>
              </div>
            )}
            <textarea
              className="w-full h-48 p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none text-gray-700"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Type or paste English text here..."
              rows="6"
            />
            <div className="mt-4 flex items-center">
              <label className="text-sm text-gray-700 mr-2">
                Translate to:
              </label>
              <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                className="py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
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
            {error && <div className="mt-2 text-red-600 text-sm">{error}</div>}
            <div className="mt-4 flex gap-3">
              {isAuthenticated && (
                <button
                  className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-4 py-2 rounded-md transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={fetchRecentEmails}
                  disabled={isTranslating || isLoading}
                >
                  View My Emails
                </button>
              )}
              <button
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-6 py-2 rounded-md transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex-1"
                onClick={handleTranslate}
                disabled={isTranslating}
              >
                {isTranslating
                  ? "Translating..."
                  : `Translate to ${selectedLanguage}`}
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-2xl font-semibold mb-4 text-gray-800">
              {selectedLanguage} Translation
            </h2>
            <div>
              <div className="min-h-[12rem] p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
                {isTranslating ? (
                  <div className="flex flex-col items-center justify-center h-full space-y-3">
                    <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-gray-600">Translating your text...</p>
                  </div>
                ) : translation ? (
                  <div className="bg-gray-50 p-6 rounded-md border border-gray-200 min-h-[10rem] shadow-inner overflow-auto">
                    <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                      {translation
                        .replace(
                          /(?:View\s+web\s+version:[\s\S]*?(?:\*{3,}[\s\S]*?(?:\n|$)|(?:\n|$))|Unfortunately[^*]*?display HTML[^*]*?browser\.[^*]*\*+)/gi,
                          ""
                        )
                        .trim()}
                    </p>
                  </div>
                ) : (
                  <p className="text-gray-500 italic text-center">
                    Your translation will appear here...
                  </p>
                )}
              </div>
              {translation && emailContent && (
                <div className="mt-4 flex justify-end">
                  <button
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg transition-all duration-200 ease-in-out flex items-center gap-2 font-medium shadow-sm hover:shadow-md"
                    onClick={async () => {
                      try {
                        // Start playing audio
                        await axios.post(
                          "http://127.0.0.1:8000/tts/speak-email",
                          {
                            email: {
                              ...emailContent,
                              original_body: emailContent.body,
                              original_subject: emailContent.subject,
                              body: translation, // translated body
                            },
                            translated_body: translation,
                            language: selectedLanguage,
                            message_id: emailContent.id,
                          }
                        );

                        // Wait for approximate playback duration (1.5 seconds per sentence)
                        const sentences = translation.split(/[.!?]+/).length;
                        const estimatedDuration = sentences * 1500;
                        await new Promise((resolve) =>
                          setTimeout(resolve, estimatedDuration)
                        );

                        // Cleanup audio file
                        await axios.post("http://127.0.0.1:8000/tts/cleanup", {
                          message_id: emailContent.id,
                          language: selectedLanguage,
                        });
                      } catch (error) {
                        setError("Unable to play audio. Please try again.");
                      }
                    }}
                  >
                    <span role="img" aria-label="speaker" className="text-xl">
                      🔊
                    </span>
                    <span>Listen</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <footer className="mt-12 text-center text-gray-600 text-sm">
        <p>Powered by Ollama LLaMA3 | MailSathi &copy; 2025</p>
      </footer>
    </div>
  );
}

export default App;
