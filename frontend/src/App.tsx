import { useCallback, useEffect, useState } from 'react';

import { type GardenOut, NinaNaturClient } from './api/client';
// Imported rather than served from `public/`, so the build names it by its
// content and it may be cached for a year — see `ninanatur/web/delivery.py`.
import meadow from './assets/meadow.mp4';
import { AccountPanel } from './components/AccountPanel';
import { FeedbackBox } from './components/FeedbackBox';
import { GardenWorkspace } from './components/GardenWorkspace';
import { Landing } from './components/Landing';
import { LivingBackground } from './components/LivingBackground';
import { MapPicker, type MapSelection } from './components/MapPicker';
import { MyGardens } from './components/MyGardens';
import { NewGardenForm } from './components/NewGardenForm';
import { PreviewBand } from './components/PreviewBand';
import { SiteHeader, type SiteProps } from './components/SiteHeader';
import { StatusToast } from './components/StatusToast';
import { objects } from './plural';
import { PlanThemeProvider } from './themes/context';
import { usePageTheme } from './themes/usePageTheme';
import { useAccount } from './useAccount';
import { useStatus } from './useStatus';

const defaultClient = new NinaNaturClient();

/**
 * The share token lives in the URL fragment, not the path or query. A fragment is
 * never sent to a server, so it cannot leak through a Referer header when the
 * user follows a link out of the app.
 */
function tokenFromHash(): string | null {
  const hash = window.location.hash.replace(/^#/, '');
  return hash.length > 0 ? hash : null;
}

/**
 * What a garden made from a map selection says once it is open: what the map
 * could and could not tell us. An assumed height presented as a measured one
 * would be the same lie as a filter that hides what it dropped.
 */
function mapSummary(heights: { measured: number; estimated: number; assumed: number }): string {
  const { measured, estimated, assumed } = heights;
  const placed = measured + estimated + assumed;
  return placed === 0
    ? 'Garten angelegt. In der Umgebung stand nichts, was Schatten wirft.'
    : // Nominative, so the sentence needs no dative the plural helper cannot
      // give it: "mit 2 Objekte" is "1 Beete" one case further on.
      `Garten angelegt. ${objects(placed)} aus der Karte übernommen — ` +
        `${measured} gemessen, ${estimated} aus Geschossen, ${assumed} angenommen.`;
}

/**
 * The site: the front door, or one open garden (doc 87).
 *
 * What outlives a garden lives here — the status line, the account and its
 * drawers, the version. Everything about the open garden lives in its workspace,
 * mounted with the garden's token as its key. The client is a prop, so the whole
 * app can be tested against a fake one.
 */
export function App({ client = defaultClient }: { client?: NinaNaturClient }) {
  const status = useStatus();
  const { setStatus, busy, run } = status;
  const [garden, setGarden] = useState<GardenOut | null>(null);
  const [openProblem, setOpenProblem] = useState<string | undefined>(undefined);
  /** What the workspace says once the garden is ready; null means "<name> geladen." */
  const [greeting, setGreeting] = useState<string | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [environment, setEnvironment] = useState<string | null>(null);
  const account = useAccount(client, status, garden === null);
  const planStyle = usePageTheme();

  /** Stable identities: an inline arrow would refire the landing page's effect
   *  on every render, which is the loop the species panel already cost us. */
  const loadStats = useCallback(async () => client.stats(), [client]);
  const findPlaces = useCallback(async (q: string) => client.findPlaces(q), [client]);
  const findImagery = useCallback(
    async (lat: number, lon: number) => client.findImagery(lat, lon),
    [client],
  );

  /** The garden itself. What the server derives from it is its workspace's to fetch. */
  const load = useCallback(
    async (token: string) => {
      const found = await client.getGarden(token);
      if (found === null) {
        // Back to the front door with the field still filled: an unknown id must
        // not look like an empty garden.
        setOpenProblem('Zu dieser ID gibt es keinen Garten.');
        setStatus('');
        return;
      }
      setOpenProblem(undefined);
      setGarden(found);
    },
    [client, setStatus],
  );

  useEffect(() => {
    const token = tokenFromHash();
    if (token !== null) {
      load(token).catch((error: unknown) =>
        setStatus(`Laden fehlgeschlagen: ${(error as Error).message}`, 'problem'),
      );
    }
    // A failed version lookup must not stop the app from loading — it is a label.
    void client.version().then(setVersion).catch(() => setVersion(null));
    // Nor a failed environment lookup. Null shows no band, which is right: the
    // live site is the one that must never be labelled by accident.
    void client.environment().then(setEnvironment).catch(() => setEnvironment(null));
  }, [client, load, setStatus]);

  /** Open one by its token — into the fragment, not a query parameter: the token
   *  is a credential, and a query would put it in the access log and any referrer. */
  const openGarden = useCallback(
    (token: string) => {
      window.location.hash = token;
      setGreeting(null);
      void run('Öffnen', () => load(token));
    },
    [load, run],
  );

  const createGarden = useCallback(
    async (input: { name: string; latitude: number; longitude: number }) => {
      await run('Anlegen', async () => {
        const created = await client.createGarden(input);
        window.location.hash = created.share_token;
        setGreeting(null);
        await load(created.share_token);
      });
    },
    [client, load, run],
  );

  const createFromMap = useCallback(
    (selection: MapSelection) => {
      void run('Anlegen', async () => {
        const result = await client.gardenFromMap(selection);
        window.location.hash = result.garden.share_token;
        setGreeting(mapSummary(result.heights));
        await load(result.garden.share_token);
      });
    },
    [client, load, run],
  );

  /** The logo goes home. Leaving a garden must not lose it — which is exactly why
   *  its id is on screen the whole time it is open. */
  const goHome = useCallback(() => {
    window.location.hash = '';
    setGarden(null);
    setStatus('');
  }, [setStatus]);

  const header: SiteProps = {
    version,
    onHome: goHome,
    onFeedback: account.openFeedback,
    accountBar: {
      username: account.account?.username ?? null,
      onSignIn: () => account.setAccountOpen(true),
      onSignUp: () => account.setAccountOpen(true),
      onSignOut: () => void account.logOut(),
      inviting: garden === null && account.account === null,
    },
  };

  return (
    // The front door is dark all the way out to the edges; a garden is not.
    <div className={garden === null ? 'app app--front-door' : 'app app--workspace'}>
      <a className="skip-link" href="#main">
        Zum Inhalt springen
      </a>
      {garden === null && <LivingBackground videoSrc={meadow} />}
      <PreviewBand environment={environment} />
      {garden === null && <SiteHeader {...header} busy={busy} />}

      {account.feedbackOpen && (
        <div className="account-drawer">
          <FeedbackBox
            questions={account.feedbackQuestions}
            onSend={account.sendFeedback}
            onClose={() => account.setFeedbackOpen(false)}
          />
        </div>
      )}

      {account.accountOpen && account.account === null && (
        <div className="account-drawer">
          <AccountPanel
            account={account.account}
            onRegister={async (input) => {
              await account.register(input);
              account.setAccountOpen(false);
            }}
            onLogin={async (input) => {
              await account.logIn(input);
              account.setAccountOpen(false);
            }}
            onLogout={account.logOut}
            busy={busy}
          />
          <button type="button" className="link-button" onClick={() => account.setAccountOpen(false)}>
            Schließen
          </button>
        </div>
      )}

      {/* The landing page has its own main, never the workspace's: rendered inside
          the garden's grid it was once handed the 22rem sidebar column. */}
      {garden === null ? (
        <main id="main" className="landing-shell">
          <Landing
            myGardens={
              account.account === null || account.myGardens === null ? undefined : (
                <MyGardens
                  gardens={account.myGardens}
                  onOpen={openGarden}
                  onDelete={account.deleteMyGarden}
                  busy={busy}
                />
              )
            }
            createForm={<NewGardenForm onCreate={createGarden} busy={busy} />}
            mapPicker={
              <MapPicker
                onCreate={createFromMap}
                busy={busy}
                search={findPlaces}
                findImagery={findImagery}
              />
            }
            onOpen={openGarden}
            busy={busy}
            loadStats={loadStats}
            problem={openProblem}
          />
        </main>
      ) : (
        <PlanThemeProvider theme={planStyle.theme}>
          <GardenWorkspace
            key={garden.share_token}
            client={client}
            garden={garden}
            setGarden={setGarden}
            status={status}
            header={header}
            account={account.account}
            planStyle={planStyle}
            greeting={greeting ?? `${garden.name} geladen.`}
          />
        </PlanThemeProvider>
      )}

      {/* Status is announced, not only shown — a colour change is invisible to a
          screen reader and to anyone not looking at that part of the page. And
          shown where it can be seen: at the page's foot it was out of sight
          whenever a list had been scrolled (doc 86). */}
      <StatusToast message={status.status} />
    </div>
  );
}
