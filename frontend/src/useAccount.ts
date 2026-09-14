import { useCallback, useEffect, useState } from 'react';

import type { FeedbackQuestions, NinaNaturClient, OwnedGardens } from './api/client';
import type { AccountInfo } from './components/AccountPanel';
import type { Status } from './useStatus';

/**
 * Who is signed in, the gardens they have kept, and the two drawers the header
 * opens. Site-wide (doc 87): all of it outlives any one garden.
 */
export function useAccount(client: NinaNaturClient, status: Status, onFrontDoor: boolean) {
  const { run, setStatus } = status;
  const [account, setAccount] = useState<AccountInfo | null>(null);
  /** The gardens this account has claimed. Null until asked. */
  const [myGardens, setMyGardens] = useState<OwnedGardens['gardens'] | null>(null);
  /** The account forms, opened from the header rather than sitting in the page. */
  const [accountOpen, setAccountOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  /** What the feedback form should ask. Fetched once, when it is first opened —
   *  nobody should pay for it on a visit that never uses it. */
  const [feedbackQuestions, setFeedbackQuestions] = useState<FeedbackQuestions | null>(null);

  // Who is logged in, asked once. Not being logged in is the ordinary state, so
  // the client answers null rather than throwing.
  useEffect(() => {
    void client.me().then(setAccount).catch(() => setAccount(null));
  }, [client]);

  // Asked whenever there is somebody to ask about, and again after a change.
  // The endpoint has existed since Wave 9; nothing had ever displayed it.
  const loadMyGardens = useCallback(async () => {
    if (account === null) {
      setMyGardens(null);
      return;
    }
    try {
      setMyGardens((await client.myGardens()).gardens);
    } catch {
      // Not being able to list them is not a reason to break the page: the
      // share link still opens a garden, which is what it is for.
      setMyGardens([]);
    }
  }, [account, client]);

  // Also when a garden closes: coming back to the front door after making or
  // deleting one must show what is actually there, not what was there when the
  // page loaded.
  useEffect(() => {
    if (onFrontDoor) void loadMyGardens();
  }, [loadMyGardens, onFrontDoor]);

  const deleteMyGarden = useCallback(
    (token: string) => {
      void run('Garten löschen', async () => {
        await client.deleteGarden(token);
        await loadMyGardens();
        setStatus('Garten gelöscht.');
      });
    },
    [client, loadMyGardens, run, setStatus],
  );

  const register = useCallback(
    async (input: { username: string; password: string; email?: string }) => {
      await run('Konto anlegen', async () => {
        await client.register(input);
        setAccount(await client.logIn({ username: input.username, password: input.password }));
        setStatus('Konto angelegt und angemeldet.');
      });
    },
    [client, run, setStatus],
  );

  const logIn = useCallback(
    async (input: { username: string; password: string }) => {
      await run('Anmelden', async () => {
        setAccount(await client.logIn(input));
        setStatus('Angemeldet.');
      });
    },
    [client, run, setStatus],
  );

  const logOut = useCallback(async () => {
    await run('Abmelden', async () => {
      await client.logOut();
      setAccount(null);
      setStatus('Abgemeldet. Deine Garten-ID öffnet den Garten weiterhin.');
    });
  }, [client, run, setStatus]);

  const openFeedback = useCallback(() => {
    setFeedbackOpen(true);
    if (feedbackQuestions === null) {
      void client.feedbackQuestions().then(setFeedbackQuestions).catch(() => undefined);
    }
  }, [client, feedbackQuestions]);

  const sendFeedback = useCallback(
    async (...args: Parameters<NinaNaturClient['sendFeedback']>) =>
      (await client.sendFeedback(...args)).message,
    [client],
  );

  return {
    account,
    myGardens,
    accountOpen,
    setAccountOpen,
    feedbackOpen,
    setFeedbackOpen,
    feedbackQuestions,
    openFeedback,
    sendFeedback,
    deleteMyGarden,
    register,
    logIn,
    logOut,
  };
}

export type Account = ReturnType<typeof useAccount>;
