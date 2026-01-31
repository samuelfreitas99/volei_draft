const socket = io();

function render() {
    fetch("/api/state")
        .then(r => r.json())
        .then(data => {
            document.getElementById("jogadores").innerHTML = "";

            data.jogadores.forEach(j => {
                if (!j.time) {
                    const div = document.createElement("div");
                    div.className = "player selectable";
                    div.innerText = j.nome;

                    if (window.CAPITAO_ID) {
                        div.onclick = () => {
                            socket.emit("pick", {
                                capitao_id: window.CAPITAO_ID,
                                jogador_id: j.id
                            });
                        };
                    }

                    document.getElementById("jogadores").appendChild(div);
                } else {
                    document.getElementById("time" + j.time)
                        .innerHTML += `<li>${j.nome}</li>`;
                }
            });
        });
}

socket.on("update", render);
render();
