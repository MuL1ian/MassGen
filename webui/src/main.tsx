import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import SetupPage from './pages/SetupPage';
import './styles/globals.css';

// Simple routing based on URL path
function Router() {
  const path = window.location.pathname;

  // Route to setup page
  if (path === '/setup' || path === '/setup/') {
    return <SetupPage />;
  }

  // Default to main app
  return <App />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Router />
  </React.StrictMode>
);
