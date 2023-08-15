import { io, Socket } from "socket.io-client";
import stripAnsi from "strip-ansi";
import {
  ContainerExit,
  ContainerStart,
  MontiorWindow,
  NewLog,
  OnConnectContainersAndLogs,
  ShortLogs,
} from "./interfaces";

declare const window: MontiorWindow;
let containers: OnConnectContainersAndLogs = {};
let active_container: string | null = null;
let should_scroll: boolean = true;

$((): void => {
  //connect to the socket server.
  let socket: Socket = io(`${document.location.origin}/main`, {
    path: "/socket.io",
  });

  socket.on("connect", () => {
    console.log("connected");
  });

  socket.on("disconnect", () => {
    console.error("disconnected");
  });

  socket.on("container_start", (data: ContainerStart) => {
    console.log("New Container: ", data.name);
    // add the container to containers
    containers[data.name] = {
      name: data.name,
      logs: [],
    };

    generate_li_list();
  });

  socket.on("connect_data", (data: OnConnectContainersAndLogs) => {
    console.log("Connect Data: ", data);
    containers = data;
    generate_li_list();
    active_container = get_first_container_sorted();
    show_logs(active_container);
  });

  socket.on("container_exit", (data: ContainerExit) => {
    console.log("Container Exit: ", data);
    // remove the container from containers
    delete containers[data.name];

    generate_li_list();
    if (active_container == data.name) {
      active_container = get_first_container_sorted();
      show_logs(active_container);
    }
  });

  // There may be an issue where the auto scroll in to view is happening when a new log entry comes in.
  // This may prevent the auto-scrolling from working. Will need more testing.
  $("#container-logs").on("scroll", function (_) {
    // Ensure we have a valid scroll_logs element
    let scroll_logs: JQuery<HTMLElement> = $("#container-logs");
    let scrollTop: number | undefined = scroll_logs.scrollTop();
    let scrollHeight: number | undefined = scroll_logs[0].scrollHeight;

    if (!scroll_logs || !scrollTop || !scrollHeight) {
      console.error("Cannot scroll right now");
      return;
    }
    // if the user is scrolling unless the user is at the bottom
    if (scrollHeight + scrollHeight < scroll_logs[0].scrollHeight) {
      should_scroll = false;
    } else {
      should_scroll = true;
    }
  });

  socket.on("new_log", (data: NewLog) => {
    // add the log message to the container
    if (!containers[data.name]) {
      console.error("Container not found: ", data.name);
      return;
    }
    containers[data.name].logs.push(data);

    while (containers[data.name].logs.length > 100) {
      containers[data.name].logs.shift();
    }

    // if the container is active, add the log to the page

    if (active_container == data.name) {
      $("#container-logs").append(generate_log_element(data));

      // if there are more than 100 logs, remove the first one
      while ($("#container-logs p").length > 100) {
        $("#container-logs p").first().remove();
      }

      if (should_scroll) {
        // get the total count of p tags
        let count: number = $("#container-logs p").length;

        let logs: HTMLElement | undefined = $("#container-logs p").get(
          count - 1
        );

        if (logs) logs.scrollIntoView({ behavior: "smooth" });
      }
    }
  });

  console.log("loaded");
});

function show_logs(name: string) {
  // clear the log list
  should_scroll = true;
  $("#container-logs").empty();

  // loop through all of the li elements and remove the class "selected" and append the class "selected" if the id matches the name
  $("#container-list li").each(function () {
    if ($(this).attr("id") == name) {
      $(this).addClass("selected");
    } else {
      $(this).removeClass("selected");
    }
  });
  active_container = name;
  let logs: ShortLogs[] = containers[name].logs;

  // add the logs to the page
  for (let log_id in logs) {
    let log = logs[log_id];
    $("#container-logs").append(generate_log_element(log));
  }
}

// ts-expect-error
window.show_logs = function (name: string) {
  show_logs(name);
};

function generate_log_element(log: ShortLogs) {
  // BE CAREFUL HERE. IF YOU CHANGE THE P TAG TO A DIFFERENT TAG, YOU MUST CHANGE THE REMOVE LOGS CODE IN THE NEW_LOG EVENT
  return `<p>${log.time} | ${stripAnsi(log.log)}</p>`;
}

function generate_li_element(name: String) {
  return `<li id="${name}" onclick="show_logs('${name}')">${name}</li>`;
}

function generate_li_list() {
  // clear the container list
  $("#container-list").empty();

  let containerNames: string[] = Object.keys(containers);
  containerNames.sort((a, b) => {
    return a.toUpperCase().localeCompare(b.toUpperCase());
  });

  // add the containers to the page
  for (let container_id in containerNames) {
    let container = containerNames[container_id];
    $("#container-list").append(
      generate_li_element(containers[container].name)
    );
  }
}

function get_first_container_sorted() {
  let containerNames: string[] = Object.keys(containers);
  containerNames.sort((a, b) => {
    return a.toUpperCase().localeCompare(b.toUpperCase());
  });

  return containerNames[0];
}
