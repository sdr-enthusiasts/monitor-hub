import { io, Socket } from "socket.io-client";

declare const window: any;
let containers: any = {};
let active_container: any = null;

$((): void => {
  let path = document.location.origin + document.location.pathname;
  path = path.endsWith("/") ? path : path + "/";

  //connect to the socket server.
  let socket = io(`${document.location.origin}/main`, {
    path: "/socket.io",
  });

  socket.on("connect", () => {
    console.log("connected");
  });

  socket.on("disconnect", () => {
    console.error("disconnected");
  });

  socket.on("new_container", (data: any) => {
    console.log("New Container: ", data.container.name);
    // add the container to containers
    containers[data.container.name] = {
      name: data.container.name,
      logs: [],
      status: data.container.status,
    };

    generate_li_list();
  });

  socket.on("connect_data", (data: any) => {
    console.log("Connect Data: ", data);
    containers = data;
    generate_li_list();
    active_container = get_first_container_sorted();
    show_logs(active_container);
  });

  socket.on("container_exit", (data: any) => {
    console.log("Container Exit: ", data);
    // remove the container from containers
    delete containers[data.name];

    generate_li_list();
    if (active_container == data.name) {
      active_container = get_first_container_sorted();
      show_logs(active_container);
    }
  });

  socket.on("new_log", (data: any) => {
    // console.log("New Log Message: ", data);
    // add the log message to the container
    if (!containers[data.name]) {
      console.error("Container not found: ", data.name);
      return;
    }
    containers[data.name].logs.push(data.log);

    // if the container is active, add the log to the page
    if (active_container == data.name) {
      $("#container-logs").append(generate_log_element(data.log));
    }
  });

  console.log("loaded");
});

function show_logs(name: any) {
  // clear the log list
  $("#container-logs").empty();

  // loop through all of the li elements and remove the class "selected" and append the class "selected" if the id matches the name
  $("#container-list li").each(function () {
    if ($(this).attr("id") == name) {
      $(this).addClass("selected");
    } else {
      $(this).removeClass("selected");
    }
  });

  let logs = containers[name].logs;

  // add the logs to the page
  for (let log_id in logs) {
    let log = logs[log_id];
    $("#container-logs").append(generate_log_element(log));
  }
}

// ts-expect-error
window.show_logs = function (name: any) {
  show_logs(name);
};

function generate_log_element(log: any) {
  return `<p>${log}</p>`;
}

function generate_li_element(name: String) {
  return `<li id="${name}" onclick="show_logs('${name}')">${name}</li>`;
}

function generate_li_list() {
  // clear the container list
  $("#container-list").empty();

  let containerNames = Object.keys(containers);
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
  let containerNames = Object.keys(containers);
  containerNames.sort((a, b) => {
    return a.toUpperCase().localeCompare(b.toUpperCase());
  });

  return containerNames[0];
}
