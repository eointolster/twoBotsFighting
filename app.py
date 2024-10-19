from flask import Flask, render_template, jsonify
import random
import numpy as np
import time

app = Flask(__name__)

class NeuralNetwork:
    def __init__(self, input_size, hidden_sizes, output_size):
        self.layers = []
        self.layers.append(np.random.randn(input_size, hidden_sizes[0]))
        for i in range(1, len(hidden_sizes)):
            self.layers.append(np.random.randn(hidden_sizes[i-1], hidden_sizes[i]))
        self.layers.append(np.random.randn(hidden_sizes[-1], output_size))

    def relu(self, x):
        return np.maximum(0, x)

    def forward(self, X):
        self.activations = [X]
        for i in range(len(self.layers) - 1):
            z = np.dot(self.activations[-1], self.layers[i])
            a = self.relu(z)
            self.activations.append(a)
        self.output = np.tanh(np.dot(self.activations[-1], self.layers[-1]))
        self.output[4] *= 0.1
        return self.output

    def mutate(self, rate=0.1):
        for layer in self.layers:
            layer += np.random.randn(*layer.shape) * rate

    def get_weights(self):
        return [layer.tolist() for layer in self.layers]

class Bot:
    MAX_SPEED = 5
    BULLET_SPEED = MAX_SPEED * 3

    def __init__(self, team, x, y):
        self.team = team
        self.x = x
        self.y = y
        self.angle = 0
        self.vision_field = np.pi/4
        self.has_fired = False
        self.neural_network = NeuralNetwork(4, [10, 10], 5)
        self.score = 0
        self.lives = 3
        self.last_shot_time = 0
        self.shot_cooldown = 2
        self.bullets_fired = 0
        self.bullets_hit = 0
        self.consecutive_hits = 0

    def can_shoot(self):
        return time.time() - self.last_shot_time >= self.shot_cooldown

    def get_inputs(self, game_state):
        enemy = self.get_nearest_enemy(game_state)
        bullet = self.get_nearest_bullet(game_state)
        return np.array([
            1 if enemy and self.in_vision_field(enemy) else 0,
            1 if bullet and self.in_vision_field(bullet) else 0,
            1 if self.can_shoot() else 0,
            self.vision_field / np.pi
        ])

    def reset_fire_flag(self):
        self.has_fired = False

    def make_decision(self, game_state):
        inputs = self.get_inputs(game_state)
        outputs = self.neural_network.forward(inputs)
        return outputs

    def in_vision_field(self, obj):
        dx = obj['x'] - self.x
        dy = obj['y'] - self.y
        angle = np.arctan2(dy, dx)
        angle_diff = (angle - self.angle + np.pi) % (2 * np.pi) - np.pi
        return abs(angle_diff) <= self.vision_field / 2

    def get_nearest_enemy(self, game_state):
        enemies = game_state['red_team'] if self.team == 'blue' else game_state['blue_team']
        if enemies:
            return min(enemies, key=lambda b: ((b['x'] - self.x)**2 + (b['y'] - self.y)**2)**0.5)
        return None

    def get_nearest_bullet(self, game_state):
        enemy_bullets = [b for b in game_state['bullets'] if b['team'] != self.team]
        if enemy_bullets:
            return min(enemy_bullets, key=lambda b: ((b['x'] - self.x)**2 + (b['y'] - self.y)**2)**0.5)
        return None

    def move(self, distance):
        new_x = self.x + np.cos(self.angle) * distance
        new_y = self.y + np.sin(self.angle) * distance

        if self.team == 'blue':
            self.x = max(0, min(new_x, 395))
        else:
            self.x = max(405, min(new_x, 800))
        
        self.y = max(0, min(new_y, 600))

    def rotate(self, angle):
        self.angle += angle
        self.angle %= 2 * np.pi

    def change_vision(self, change):
        self.vision_field = max(0.1, min(self.vision_field + change, np.pi))

    def fire_bullet(self):
        if self.can_shoot():
            spread = random.uniform(-self.vision_field / 2, self.vision_field / 2)
            bullet_angle = self.angle + spread
            
            bullet = {
                'x': self.x,
                'y': self.y,
                'angle': bullet_angle,
                'team': self.team
            }
            self.last_shot_time = time.time()
            self.bullets_fired += 1
            return bullet
        return None

class Game:
    def __init__(self):
        self.blue_bot = Bot('blue', random.uniform(100, 300), random.uniform(100, 500))
        self.red_bot = Bot('red', random.uniform(500, 700), random.uniform(100, 500))
        self.blue_bot.angle = random.uniform(0, 2 * np.pi)
        self.red_bot.angle = random.uniform(0, 2 * np.pi)
        self.bullets = []
        self.generation = 0
        self.generation_start_time = time.time()

    def update(self):
        game_state = self.get_game_state()
        blue_decision = self.blue_bot.make_decision(game_state)
        red_decision = self.red_bot.make_decision(game_state)

        self.blue_bot.reset_fire_flag()
        self.red_bot.reset_fire_flag()        
        self.execute_decision(self.blue_bot, blue_decision)
        self.execute_decision(self.red_bot, red_decision)
        
        self.move_bullets()
        self.check_collisions()

    def execute_decision(self, bot, decision):
        move_forward, turn_left, turn_right, fire, change_vision = decision
        
        bot.move(move_forward * bot.MAX_SPEED)
        bot.rotate((turn_right - turn_left) * 0.1)
        bot.change_vision(change_vision * 0.1)
        
        if fire > 0 and bot.can_shoot():
            new_bullet = bot.fire_bullet()
            if new_bullet:
                self.bullets.append(new_bullet)

    def move_bullets(self):
        for bullet in self.bullets:
            bullet['x'] += np.cos(bullet['angle']) * Bot.BULLET_SPEED
            bullet['y'] += np.sin(bullet['angle']) * Bot.BULLET_SPEED
        self.bullets = [b for b in self.bullets if 0 <= b['x'] <= 800 and 0 <= b['y'] <= 600]

    def check_collisions(self):
        for bullet in self.bullets[:]:
            for bot in [self.blue_bot, self.red_bot]:
                if bullet['team'] != bot.team:
                    distance = ((bot.x - bullet['x'])**2 + (bot.y - bullet['y'])**2)**0.5
                    if distance < 15:
                        bot.lives -= 1
                        self.bullets.remove(bullet)
                        shooting_bot = self.blue_bot if bullet['team'] == 'blue' else self.red_bot
                        
                        # Increased reward for hitting
                        base_hit_reward = 500
                        shooting_bot.score += base_hit_reward
                        
                        # Additional reward for consecutive hits
                        shooting_bot.consecutive_hits += 1
                        if shooting_bot.consecutive_hits > 1:
                            shooting_bot.score += base_hit_reward * shooting_bot.consecutive_hits
                        
                        shooting_bot.bullets_hit += 1
                        break
                    elif distance < 30:
                        bot.score += 5  # Small bonus for near dodge
                    elif distance > 100:  # Punishment for missing by a large margin
                        shooting_bot = self.blue_bot if bullet['team'] == 'blue' else self.red_bot
                        shooting_bot.score -= 50  # Penalty for very poor aim
                        shooting_bot.consecutive_hits = 0  # Reset consecutive hits

        # Small reward for shooting, to encourage action
        for bot in [self.blue_bot, self.red_bot]:
            if bot.bullets_fired > 0:
                bot.score += bot.bullets_fired * 2  # 2 points per bullet fired

        # Penalty for inactivity
        for bot in [self.blue_bot, self.red_bot]:
            if bot.bullets_fired == 0:
                bot.score -= 10  # Increased penalty for not shooting

        # Reset bullet counters
        self.blue_bot.bullets_fired = 0
        self.red_bot.bullets_fired = 0

    def get_game_state(self):
        game_state = {
            'blue_team': [{'x': self.blue_bot.x, 'y': self.blue_bot.y, 'angle': self.blue_bot.angle, 'vision_field': self.blue_bot.vision_field}],
            'red_team': [{'x': self.red_bot.x, 'y': self.red_bot.y, 'angle': self.red_bot.angle, 'vision_field': self.red_bot.vision_field}],
            'bullets': self.bullets
        }
        
        blue_inputs = self.blue_bot.get_inputs(game_state)
        blue_outputs = self.blue_bot.make_decision(game_state)
        red_inputs = self.red_bot.get_inputs(game_state)
        red_outputs = self.red_bot.make_decision(game_state)
        
        game_state['blue_network'] = {
            'inputs': blue_inputs.tolist(),
            'outputs': blue_outputs.tolist(),
            'weights': self.blue_bot.neural_network.get_weights()
        }
        game_state['red_network'] = {
            'inputs': red_inputs.tolist(),
            'outputs': red_outputs.tolist(),
            'weights': self.red_bot.neural_network.get_weights()
        }
        
        return game_state

    def run_tournament(self):
        if self.blue_bot.lives > self.red_bot.lives:
            self.blue_bot.score += 3
        elif self.red_bot.lives > self.blue_bot.lives:
            self.red_bot.score += 3
        else:
            self.blue_bot.score += 1
            self.red_bot.score += 1

    def evolve(self):
        self.generation += 1
        self.blue_bot.neural_network.mutate()
        self.red_bot.neural_network.mutate()
        self.reset_round()
        self.generation_start_time = time.time()

    def reset_round(self):
        self.blue_bot.x, self.blue_bot.y = 200, 300
        self.red_bot.x, self.red_bot.y = 600, 300
        self.blue_bot.lives = self.red_bot.lives = 3
        self.blue_bot.bullets_fired = self.blue_bot.bullets_hit = 0
        self.red_bot.bullets_fired = self.red_bot.bullets_hit = 0
        self.blue_bot.score = self.red_bot.score = 0  # Reset scores at the start of each round
        self.bullets.clear()


    def get_scores(self):
        blue_score = (3 - self.blue_bot.lives) * -1000 + self.blue_bot.score
        red_score = (3 - self.red_bot.lives) * -1000 + self.red_bot.score
        return blue_score, red_score

    def run_tournament(self):
        if self.blue_bot.lives > self.red_bot.lives:
            self.blue_bot.score += 500
        elif self.red_bot.lives > self.blue_bot.lives:
            self.red_bot.score += 500
        else:
            self.blue_bot.score += 250
            self.red_bot.score += 250

game = Game()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_state', methods=['GET'])
def get_state():
    return jsonify(game.get_game_state())

@app.route('/update', methods=['POST'])
def update_game():
    game.update()
    return jsonify(game.get_game_state())

@app.route('/evolve', methods=['POST'])
def evolve_game():
    game.evolve()
    return jsonify({"status": "evolved", "generation": game.generation})

@app.route('/get_scores', methods=['GET'])
def get_scores():
    blue_score, red_score = game.get_scores()
    return jsonify({
        "blue_score": blue_score,
        "red_score": red_score,
        "blue_lives": game.blue_bot.lives,
        "red_lives": game.red_bot.lives,
        "generation": game.generation
    })

if __name__ == '__main__':
    app.run(debug=True)