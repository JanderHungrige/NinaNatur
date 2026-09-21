/**
 * The keyboard's shortcuts, as the help lists them (doc 92).
 *
 * Only what the code answers, grouped by where it applies, with every key named
 * the way a German keyboard labels it. On a Mac the help says once that ⌘
 * stands for Strg, rather than listing every chord twice.
 */

/** Keys held together. */
export type Chord = readonly string[];

export interface Shortcut {
  /** One chord, or several that do the same. */
  readonly keys: readonly Chord[];
  readonly does: string;
}

export interface ShortcutGroup {
  readonly heading: string;
  readonly shortcuts: readonly Shortcut[];
}

export const SHORTCUTS: readonly ShortcutGroup[] = [
  {
    heading: 'Überall',
    shortcuts: [
      { keys: [['?']], does: 'Zeigt diese Übersicht.' },
      {
        keys: [['Esc']],
        does:
          'Legt das Werkzeug ab, verwirft eine angefangene Form und hebt die Auswahl auf. ' +
          'In einem offenen Menü schließt es nur das Menü.',
      },
      { keys: [['Strg', 'Z']], does: 'Macht die letzte Änderung rückgängig.' },
    ],
  },
  {
    heading: 'Im Plan',
    shortcuts: [
      {
        keys: [['Tab']],
        does:
          'Geht durch die Beete, Objekte und Pflanzflächen. Solange ein Werkzeug gewählt ist, ' +
          'nur durch die Pflanzflächen.',
      },
      {
        keys: [['Eingabe'], ['Leertaste']],
        does:
          'Wählt aus, was den Fokus hat. Auf dem i über einer gewählten Pflanzfläche: zeigt die ' +
          'Angaben zur Art.',
      },
      {
        keys: [['Umschalt', 'F10'], ['Kontextmenü']],
        does: 'Wählt das Beet oder Objekt mit dem Fokus und springt in seine Angaben.',
      },
      { keys: [['Strg', 'C']], does: 'Kopiert die gewählte Pflanzfläche: ihre Art und wie viele.' },
      {
        keys: [['Strg', 'V']],
        does: 'Pflanzt sie noch einmal, ins gewählte Beet oder ins Beet der gewählten Pflanzfläche.',
      },
      { keys: [['Mausrad']], does: 'Zoomt dort, wo der Zeiger steht.' },
      {
        keys: [['Alt']],
        does: 'Gedrückt gehalten: setzt eine Ecke frei, ohne einzurasten, und dreht ohne 15°-Schritte.',
      },
    ],
  },
  {
    heading: 'In der Werkzeugleiste',
    shortcuts: [
      { keys: [['Pfeiltasten']], does: 'Geht von Werkzeug zu Werkzeug, nach dem letzten wieder zum ersten.' },
      { keys: [['Pos1'], ['Ende']], does: 'Springt zum ersten oder zum letzten Werkzeug.' },
    ],
  },
  {
    heading: 'In den Vorschlägen',
    shortcuts: [
      { keys: [['↑'], ['↓']], does: 'Geht zum vorigen oder zum nächsten Vorschlag.' },
      { keys: [['Bild↑'], ['Bild↓']], does: 'Blättert um so viele Vorschläge, wie das Fenster zeigt.' },
      { keys: [['Pos1'], ['Ende']], does: 'Springt zum ersten oder zum letzten Vorschlag.' },
    ],
  },
  {
    heading: 'Auf einem schmalen Fenster',
    shortcuts: [
      { keys: [['↑'], ['↓']], does: 'Am Griff der Details: hebt sie eine Stufe oder senkt sie eine.' },
      { keys: [['Pos1'], ['Ende']], does: 'Am Griff: senkt die Details auf ein Viertel oder hebt sie fast ganz.' },
      { keys: [['Eingabe']], does: 'Am Griff: wechselt zwischen gut der Hälfte und einem Viertel.' },
      { keys: [['Esc']], does: 'In fast ganz gehobenen Details: senkt sie auf gut die Hälfte.' },
    ],
  },
];
