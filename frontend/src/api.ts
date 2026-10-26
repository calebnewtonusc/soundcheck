import type { Pass, Profile, Source } from "./profiles";

export type Player = {
  id: string;
  name: string;
  score: number;
  source: "spotify" | "sample" | "picks" | "export";
  bot: boolean;
  avatar: string | null;
  streak: number;
  right: number;
  answered: boolean;
  team: "red" | "blue" | null;
};

export type Mode = "classic" | "wrapped" | "roadtrip" | "decades" | "genres";
export const REACTIONS = ["CALLED IT", "NO WAY", "SUS", "RESPECT"] as const;

export type Option = {
  id: string;
  label: string;
  sub: string;
  image: string | null;
};

export type Card = {
  id: string;
  title: string;
  color: "red" | "mustard" | "green" | "blue";
  winner: string;
  pid: string;
  stat: string;
};

export type RoomState = {
  code: string;
  phase: "lobby" | "question" | "reveal" | "report";
  version: number;
  host_id: string | null;
  length: number;
  mode: Mode;
  teams: boolean;
  ai: boolean;
  me: string | null;
  team_scores?: { red: number; blue: number };
  season?: Season;
  players: Player[];
  question?: {
    index: number;
    total: number;
    category: "songs" | "artists" | "genre";
    kind: "who" | "pick";
    text: string;
    image: string | null;
    options: Option[];
    seconds: number;
    time_left: number;
    about_me: boolean;
    my_answer: string | null;
    waiting_on: number;
  };
  reveal?: {
    correct: string[];
    subjects: string[];
    explain: string;
    picks: Record<string, string>;
    points: Record<string, number>;
    reactions: [string, string][];
  };
  cards?: Card[];
};

export type Creds = { pid: string; key: string };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = "Something went wrong. Try again.";
    try {
      const body: unknown = await res.json();
      if (
        body &&
        typeof body === "object" &&
        "detail" in body &&
        typeof body.detail === "string"
      )
        detail = body.detail;
    } catch {
      // Non-JSON error body: keep the generic message.
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

const post = <T>(path: string, body: unknown) =>
  call<T>(path, { method: "POST", body: JSON.stringify(body) });

export type Season = { games: number; table: { id: string; name: string; wins: number; points: number; here: boolean }[] };

export const api = {
  joinProfile: (code: string, name: string, source: Source, profile: Profile, avatar: string | null = null) =>
    post<Creds>(`/api/rooms/${code}/join-profile`, { name, source, profile, avatar }),
  updateProfile: (code: string, c: Creds, source: Source, profile: Profile) => post<RoomState>(`/api/rooms/${code}/profile`, { ...c, source, profile }),
  myProfile: (code: string, c: Creds) => post<Omit<Pass, "saved">>(`/api/rooms/${code}/my-profile`, c),
  create: () => post<{ code: string }>("/api/rooms", {}),
  state: (code: string, c: Creds | null) => call<RoomState>(`/api/rooms/${code}?${new URLSearchParams(c ? { pid: c.pid, key: c.key } : {})}`),
  joinSample: (code: string, name: string, recent: boolean) => post<Creds>(`/api/rooms/${code}/join-sample`, { name, recent }),
  bots: (code: string, c: Creds) => post<RoomState>(`/api/rooms/${code}/bots`, c),
  leave: (code: string, c: Creds) => post<RoomState>(`/api/rooms/${code}/leave`, c),
  kick: (code: string, c: Creds, target: string) => post<RoomState>(`/api/rooms/${code}/kick/${target}`, c),
  settings: (code: string, c: Creds, s: { length?: number; mode?: Mode; teams?: boolean; ai?: boolean }) =>
    post<RoomState>(`/api/rooms/${code}/settings`, { ...c, ...s }),
  shuffleTeams: (code: string, c: Creds) => post<RoomState>(`/api/rooms/${code}/shuffle-teams`, c),
  react: (code: string, c: Creds, label: string) => post<RoomState>(`/api/rooms/${code}/react`, { ...c, label }),
  start: (code: string, c: Creds) => post<RoomState>(`/api/rooms/${code}/start`, c),
  answer: (code: string, c: Creds, choice: string) => post<RoomState>(`/api/rooms/${code}/answer`, { ...c, choice }),
  next: (code: string, c: Creds) => post<RoomState>(`/api/rooms/${code}/next`, c),
  rematch: (code: string, c: Creds) => post<RoomState>(`/api/rooms/${code}/rematch`, c),
  health: () => call<{ spotify: boolean; ai: boolean; search: boolean }>("/api/health"),
  loginUrl: (code: string, name: string, recent: boolean) =>
    `/api/login?${new URLSearchParams({ room: code, name, tz: String(new Date().getTimezoneOffset()), recent: recent ? "1" : "0" })}`,
};

const KEY = (code: string) => `soundcheck:${code}`;

export function loadCreds(code: string): Creds | null {
  try {
    const raw = localStorage.getItem(KEY(code));
    if (!raw) return null;
    const v: unknown = JSON.parse(raw);
    if (
      v &&
      typeof v === "object" &&
      "pid" in v &&
      "key" in v &&
      typeof v.pid === "string" &&
      typeof v.key === "string"
    ) {
      return { pid: v.pid, key: v.key };
    }
  } catch {
    // Private mode or blocked storage: the player rejoins.
  }
  return null;
}

export function saveCreds(code: string, c: Creds) {
  try {
    localStorage.setItem(KEY(code), JSON.stringify(c));
  } catch {
    // Storage blocked: creds live only in memory for this tab.
  }
}

export function clearCreds(code: string) {
  try {
    localStorage.removeItem(KEY(code));
  } catch {
    // Nothing stored to clear.
  }
}
