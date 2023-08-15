export interface NewLog {
  name: string;
  time: number;
  log: string;
}

export interface ShortLogs {
  time: number;
  log: string;
}

export interface ContainerExit {
  name: string;
}

export interface ContainerStart {
  name: string;
}

export interface OnConnectContainersAndLogs {
  [key: string]: {
    name: string;
    logs: ShortLogs[];
  };
}

export interface MontiorWindow extends Window {
  show_logs: (name: string) => void;
}
