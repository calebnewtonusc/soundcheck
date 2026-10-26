export type Player = {
  id: string;
  name: string;
  score: number;
  source: "spotify" | "sample";
  bot: boolean;
  answered: boolean;
};

export type RoomState = {
  code: string;
  phase: "lobby" | "question" | "reveal" | "report";
  host_id: string | null;
  me: string | null;
  players: Player[];
  question?: {
    index: number;
    total: number;
    category: "songs" | "artists" | "genre";
    text: string;
    seconds: number;
    time_left: number;
    about_me: boolean;
    my_answer: string | null;
  };
  reveal?: {
    correct: string[];
    subject: string;
    explain: string;
    picks: Record<string, string>;
    points: Record<string, number>;
  };
  cards?: {
    id: string;
    title: string;
    color: "red" | "mustard" | "green" | "blue";
    winner: string;
    stat: string;
  }[];
};

export type Creds = { pid: string; key: string };

export class ApiError extends Error {}

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
    throw new ApiError(detail);
  }
  return (await res.json()) as T;
}

const post = <T>(path: string, body: unknown) =>
  call<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  create: () => post<{ code: string }>("/api/rooms", {}),
  state: (code: string, c: Creds | null) =>
    call<RoomState>(
      `/api/rooms/${code}?${new URLSearchParams(c ? { pid: c.pid, key: c.key } : {})}`,
    ),
  joinSample: (code: string, name: string) =>
    post<Creds>(`/api/rooms/${code}/join-sample`, { name }),
  bots: (code: string, c: Creds) =>
    post<RoomState>(`/api/rooms/${code}/bots`, c),
  start: (code: string, c: Creds) =>
    post<RoomState>(`/api/rooms/${code}/start`, c),
  answer: (code: string, c: Creds, choice: string) =>
    post<RoomState>(`/api/rooms/${code}/answer`, { ...c, choice }),
  next: (code: string, c: Creds) =>
    post<RoomState>(`/api/rooms/${code}/next`, c),
  rematch: (code: string, c: Creds) =>
    post<RoomState>(`/api/rooms/${code}/rematch`, c),
  health: () => call<{ spotify: boolean }>("/api/health"),
  loginUrl: (code: string, name: string) =>
    `/api/login?${new URLSearchParams({ room: code, name })}`,
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
