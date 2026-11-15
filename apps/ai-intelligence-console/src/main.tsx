import {createRoot} from 'react-dom/client';
import {devobsAuth} from './services/devobsAuthFacade';
import './index.css';

async function start() {
  // Consume/scrub the provider response before Google/Firebase or other app
  // modules initialize. No auth initialization happens on ordinary page loads.
  await devobsAuth.handleCallback(window.location.href);
  const {default: App} = await import('./App.tsx');
  createRoot(document.getElementById('root')!).render(<App />);
}

void start();
