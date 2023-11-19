export interface RawA11yResponse {
  data: RawA11yFrame[];
}

export interface RawA11yFrame {
  elements: A11yIssueElement[];
  help: string;
  help_url: string;
  id: string;
  timestamp: number;
  impact?: 'minor' | 'moderate' | 'serious' | 'critical';
}

interface A11yIssueElement {
  alternatives: A11yIssueElementAlternative[];
  element: string;
  target: string[];
}

interface A11yIssueElementAlternative {
  id: string;
  message: string;
}

type Overwrite<T, U> = Pick<T, Exclude<keyof T, keyof U>> & U;

export type HydratedA11yFrame = Overwrite<
  Omit<RawA11yFrame, 'elements'>,
  {
    /**
     * The specific element instance
     */
    element: A11yIssueElement;
    /**
     * The difference in timestamp and replay.started_at, in millieseconds
     */
    offsetMs: number;
    /**
     * The Date when the a11yIssue happened
     */
    timestamp: Date;
    /**
     * Alias of timestamp, in milliseconds
     */
    timestampMs: number;
  }
>;

export default function hydrateA11yFrame(
  raw: RawA11yFrame,
  startTimestampMs: number
): HydratedA11yFrame[] {
  return raw.elements.map((element): HydratedA11yFrame => {
    const timestamp = new Date(raw.timestamp);
    const timestampMs = timestamp.getTime();
    return {
      element,
      help_url: raw.help_url,
      help: raw.help,
      id: raw.id,
      impact: raw.impact,
      offsetMs: timestampMs - startTimestampMs,
      timestamp,
      timestampMs,
    };
  });
}
