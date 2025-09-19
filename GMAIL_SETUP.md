# Gmail Integration Setup Guide

## Overview

This guide will help you set up the Gmail API integration for MailSathi. This feature allows you to connect your Gmail account, view your recent emails, and translate them to Marathi.

## Prerequisites

1. A Google Cloud Platform (GCP) account
2. Basic understanding of OAuth 2.0

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project"
3. Enter a name for your project (e.g., "MailSathi")
4. Click "Create"

## Step 2: Enable the Gmail API

1. Go to the [API Library](https://console.cloud.google.com/apis/library) in your Google Cloud Console
2. Search for "Gmail API"
3. Click on "Gmail API"
4. Click "Enable"

## Step 3: Create OAuth Credentials

1. Go to the [Credentials page](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Web application" as the application type
4. Enter a name for your OAuth client (e.g., "MailSathi Web Client")
5. Add authorized redirect URIs:
   - `http://localhost:8000/auth/callback`
6. Click "Create"
7. Note down your client ID and client secret

## Step 4: Configure Your Application

1. Copy the `.env.example` file to `.env` in the backend directory:
   ```
   cp .env.example .env
   ```
2. Edit the `.env` file and add your client ID and client secret:
   ```
   GMAIL_CLIENT_ID=your_client_id_here
   GMAIL_CLIENT_SECRET=your_client_secret_here
   ```

## Step 5: Start the Application

1. Start the backend server:
   ```
   cd backend
   uvicorn main:app --reload --port 8000
   ```
2. Start the frontend development server:
   ```
   cd frontend
   npm run dev
   ```

## Using the Gmail Integration

1. Open the MailSathi application in your browser (usually at http://localhost:5173 or http://localhost:5174)
2. Click the "Connect Gmail Account" button
3. Sign in to your Google account and authorize the application
4. Once connected, click "View My Emails" to see your recent emails
5. Click on an email to view its content, or click "Translate" to directly translate it to Marathi

## Note on Security

This implementation is for development purposes only. In a production environment, you would need to:

1. Implement proper user authentication and session management
2. Store credentials securely in a database
3. Use HTTPS for all communications
4. Implement proper error handling and logging
5. Consider refreshing tokens and handling token expiration
