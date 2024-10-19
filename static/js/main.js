const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const BOT_RADIUS = 15;
const BULLET_RADIUS = 3;

let generation = 0;
let blueScore = 0;
let redScore = 0;
let blueLives = 3;
let redLives = 3;

function drawBot(bot) {
    // Draw bot body
    ctx.fillStyle = bot.team === 'blue' ? 'blue' : 'red';
    ctx.beginPath();
    ctx.arc(bot.x, bot.y, BOT_RADIUS, 0, 2 * Math.PI);
    ctx.fill();

    // Draw vision field
    ctx.fillStyle = bot.team === 'blue' ? 'rgba(0, 0, 255, 0.2)' : 'rgba(255, 0, 0, 0.2)';
    ctx.beginPath();
    ctx.moveTo(bot.x, bot.y);
    ctx.arc(bot.x, bot.y, BOT_RADIUS * 5, bot.angle - bot.vision_field / 2, bot.angle + bot.vision_field / 2);
    ctx.closePath();
    ctx.fill();

    // Draw direction indicator
    ctx.strokeStyle = 'white';
    ctx.beginPath();
    ctx.moveTo(bot.x, bot.y);
    ctx.lineTo(bot.x + Math.cos(bot.angle) * BOT_RADIUS, bot.y + Math.sin(bot.angle) * BOT_RADIUS);
    ctx.stroke();

    // Indicate if the bot is shooting
    if (bot.has_fired) {
        ctx.strokeStyle = 'yellow';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(bot.x, bot.y, BOT_RADIUS + 5, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.lineWidth = 1;
    }

    // Indicate cooldown status
    if (!bot.can_shoot) {
        ctx.strokeStyle = 'gray';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(bot.x, bot.y, BOT_RADIUS + 5, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.lineWidth = 1;
    }
}

function drawBullet(bullet) {
    ctx.fillStyle = bullet.team === 'blue' ? 'darkblue' : 'darkred';
    ctx.beginPath();
    ctx.arc(bullet.x, bullet.y, BULLET_RADIUS, 0, 2 * Math.PI);
    ctx.fill();

    // Draw a line indicating bullet direction
    ctx.strokeStyle = bullet.team === 'blue' ? 'blue' : 'red';
    ctx.beginPath();
    ctx.moveTo(bullet.x, bullet.y);
    ctx.lineTo(bullet.x + Math.cos(bullet.angle) * 10, bullet.y + Math.sin(bullet.angle) * 10);
    ctx.stroke();
}

function drawGame(gameState) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw middle line
    ctx.strokeStyle = 'black';
    ctx.beginPath();
    ctx.moveTo(400, 0);
    ctx.lineTo(400, 600);
    ctx.stroke();

    gameState.blue_team.forEach(bot => drawBot({...bot, team: 'blue'}));
    gameState.red_team.forEach(bot => drawBot({...bot, team: 'red'}));
    gameState.bullets.forEach(drawBullet);

    // Draw lives
    ctx.font = '20px Arial';
    ctx.fillStyle = 'blue';
    ctx.fillText(`Lives: ${blueLives}`, 10, 30);
    ctx.fillStyle = 'red';
    ctx.fillText(`Lives: ${redLives}`, canvas.width - 100, 30);
}

function updateGame() {
    fetch('/update', { method: 'POST' })
        .then(response => response.json())
        .then(gameState => {
            console.log('Received game state:', gameState);
            if (gameState.blue_team && gameState.red_team) {
                drawGame(gameState);
                updateScores();
                if (gameState.blue_network && gameState.blue_network.weights) {
                    console.log('Blue network data:', gameState.blue_network);
                    drawNeuralNet('blueNeuralNet', gameState.blue_network.inputs, gameState.blue_network.outputs, gameState.blue_network.weights);
                } else {
                    console.error('Invalid blue network data');
                }
                if (gameState.red_network && gameState.red_network.weights) {
                    console.log('Red network data:', gameState.red_network);
                    drawNeuralNet('redNeuralNet', gameState.red_network.inputs, gameState.red_network.outputs, gameState.red_network.weights);
                } else {
                    console.error('Invalid red network data');
                }
            } else {
                console.error('Invalid game state received:', gameState);
            }
        })
        .catch(error => console.error('Error updating game:', error));
}

function evolve() {
    fetch('/evolve', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log('Evolved to generation:', data.generation);
            generation = data.generation;
            updateScores();  // Update scores immediately after evolution
        })
        .catch(error => console.error('Error during evolution:', error));
}

function updateScores() {
    fetch('/get_scores')
        .then(response => response.json())
        .then(data => {
            blueScore = data.blue_score;
            redScore = data.red_score;
            blueLives = data.blue_lives;
            redLives = data.red_lives;
            generation = data.generation;
            updateScoreDisplay();
        })
        .catch(error => console.error('Error updating scores:', error));
}

function updateScoreDisplay() {
    document.getElementById('generationDisplay').textContent = `Generation: ${generation}`;
    document.getElementById('blueScoreDisplay').textContent = `Blue Score: ${blueScore}`;
    document.getElementById('redScoreDisplay').textContent = `Red Score: ${redScore}`;
    document.getElementById('blueLivesDisplay').textContent = `Blue Lives: ${blueLives}`;
    document.getElementById('redLivesDisplay').textContent = `Red Lives: ${redLives}`;
}

// Make sure these intervals are set
let gameInterval = setInterval(updateGame, 100);  // Update game every 100ms
let evolutionInterval = setInterval(evolve, 30000);  // Evolve every 30 seconds

function toggleSimulation() {
    if (gameInterval) {
        clearInterval(gameInterval);
        clearInterval(evolutionInterval);
        gameInterval = null;
        evolutionInterval = null;
        document.getElementById('toggleButton').textContent = 'Start Simulation';
    } else {
        gameInterval = setInterval(updateGame, 100);
        evolutionInterval = setInterval(evolve, 30000);
        document.getElementById('toggleButton').textContent = 'Pause Simulation';
    }
}


function drawNeuralNet(netId, inputs, outputs, weights) {
    const canvas = document.getElementById(netId);
    if (!canvas || !canvas.getContext) {
        console.error(`Canvas with id ${netId} not found or doesn't support 2d context`);
        return;
    }
    const ctx = canvas.getContext('2d');
    
    // Adjust canvas size
    canvas.width = 400;
    canvas.height = 600;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const inputLabels = ['Enemy', 'Bullet', 'CanShoot', 'Vision'];
    const outputLabels = ['Move', 'TurnL', 'TurnR', 'Fire', 'ChgVis'];

    if (!weights || !weights.length) {
        console.error(`Invalid weights for ${netId}`);
        return;
    }

    const layerSizes = [inputs.length, ...weights.map(w => w.length), outputs.length];
    const layers = layerSizes.length;
    const maxLayerSize = Math.max(...layerSizes);

    const nodeRadius = 8;
    const layerHeight = (canvas.height - 100) / Math.max(inputLabels.length, outputLabels.length);
    const layerWidth = (canvas.width - 200) / (layers - 1);

    // Scale factor for weight visualization
    const scaleFactor = 3;

    // Draw nodes and connections
    for (let l = 0; l < layers; l++) {
        for (let n = 0; n < layerSizes[l]; n++) {
            const x = 100 + l * layerWidth;
            const y = 50 + n * (canvas.height - 100) / (layerSizes[l] - 1);

            // Draw connections to next layer
            if (l < layers - 1 && weights[l] && weights[l][n]) {
                for (let nextN = 0; nextN < layerSizes[l + 1]; nextN++) {
                    const nextX = 100 + (l + 1) * layerWidth;
                    const nextY = 50 + nextN * (canvas.height - 100) / (layerSizes[l + 1] - 1);
                    ctx.beginPath();
                    ctx.moveTo(x, y);
                    ctx.lineTo(nextX, nextY);
                    const weight = weights[l][n][nextN];
                    if (weight !== undefined) {
                        ctx.strokeStyle = weight > 0 ? `rgba(0, 0, 255, ${Math.min(Math.abs(weight) * scaleFactor, 1)})` : `rgba(255, 0, 0, ${Math.min(Math.abs(weight) * scaleFactor, 1)})`;
                        ctx.lineWidth = Math.abs(weight) * 2 * scaleFactor;
                        ctx.stroke();
                    }
                }
            }

            // Draw node
            ctx.beginPath();
            ctx.arc(x, y, nodeRadius, 0, 2 * Math.PI);
            ctx.fillStyle = l === 0 ? 'lightgreen' : l === layers - 1 ? 'lightblue' : 'lightpink';
            ctx.fill();
            ctx.stroke();
        }
    }

    // Draw labels
    ctx.fillStyle = 'black';
    ctx.font = '12px Arial';
    ctx.textAlign = 'right';
    for (let i = 0; i < inputLabels.length; i++) {
        const x = 90;
        const y = 55 + i * layerHeight;
        ctx.fillText(`${inputLabels[i]}: ${inputs[i].toFixed(2)}`, x, y);
    }
    ctx.textAlign = 'left';
    for (let i = 0; i < outputLabels.length; i++) {
        const x = canvas.width - 90;
        const y = 55 + i * layerHeight;
        ctx.fillText(`${outputLabels[i]}: ${outputs[i].toFixed(2)}`, x, y);
    }

    // Draw titles
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText("Inputs", 50, 30);
    ctx.fillText("Outputs", canvas.width - 50, 30);

    // Draw legend
    ctx.font = '10px Arial';
    ctx.textAlign = 'left';
    ctx.fillText("Blue: +ve weight", 10, canvas.height - 25);
    ctx.fillText("Red: -ve weight", 10, canvas.height - 10);
}

// Add this function to check if intervals are running
function checkIntervals() {
    console.log('Game interval ID:', gameInterval);
    console.log('Evolution interval ID:', evolutionInterval);
}

// Call this function after a short delay
setTimeout(checkIntervals, 1000);

// Initial update
updateGame();
updateScores();