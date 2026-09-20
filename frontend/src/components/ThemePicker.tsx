import type { ThemeOnOffer } from '../themes';

/**
 * Which style the plan is drawn in (doc 100), in the menu that already holds
 * what acts on the whole garden.
 *
 * Radio buttons rather than a select: there are two of them, the choice is
 * worth seeing, and a third style is meant to fit. Drawn only where more than
 * one style is on offer, so a deployment carries no control for something it
 * will not serve.
 */
interface Props {
  options: readonly ThemeOnOffer[];
  chosen: string;
  onChoose: (id: string) => void;
  /** With high contrast the plan is Technisch whatever was chosen, and saying
   *  so is better than a control that disagrees with the drawing. */
  overridden?: boolean;
}

export function ThemePicker({ options, chosen, onChoose, overridden = false }: Props) {
  if (options.length < 2) return null;
  return (
    <fieldset className="theme-picker">
      <legend className="theme-picker__legend">Planstil</legend>
      {options.map((theme) => (
        <label key={theme.id} className="theme-picker__choice">
          <input
            type="radio"
            name="plan-theme"
            value={theme.id}
            checked={theme.id === chosen}
            disabled={overridden}
            onChange={() => onChoose(theme.id)}
          />
          {theme.label}
        </label>
      ))}
      {overridden && (
        <p className="theme-picker__note">
          Bei hohem Kontrast wird immer der technische Plan gezeichnet.
        </p>
      )}
    </fieldset>
  );
}
