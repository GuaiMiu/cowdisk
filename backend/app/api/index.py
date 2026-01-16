"""
@File: index.py
@Author: GuaiMiu
@Date: 2025/4/14 15:22
@Version: 1.0
@Description:
"""

from fastapi import APIRouter
from starlette.responses import HTMLResponse, FileResponse

index_router = APIRouter(tags=["index"])


@index_router.get("/")
async def index():
    """
    首页
    :return:
    """
    return HTMLResponse(content="ok")


@index_router.get("/favicon.ico")
async def favicon():
    """
    返回 favicon.ico
    :return:
    """
    return FileResponse("app/static/images/logo.ico")


@index_router.get("/fish")
async def get_fish_animation():
    # 将 HTML 页面返回作为响应
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>笨牛小鱼</title>
    <style>
        body {
            margin: 0;
            overflow: hidden;
            background: linear-gradient(to bottom, #87CEEB, #1E3B70);
        }
        canvas {
            display: block;
        }
        #info {
            position: absolute;
            top: 10px;
            width: 100%;
            text-align: center;
            z-index: 100;
            color: white;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 24px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }
        #controls {
            position: absolute;
            bottom: 20px;
            left: 20px;
            color: white;
            font-family: Arial, sans-serif;
            background: rgba(0, 0, 0, 0.5);
            padding: 10px;
            border-radius: 5px;
        }
        .control-buttons {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: grid;
            grid-template-columns: repeat(3, 60px);
            grid-template-rows: repeat(3, 60px);
            gap: 5px;
            z-index: 1000;
        }
        .control-button {
            width: 60px;
            height: 60px;
            border: none;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            color: white;
            font-size: 24px;
            cursor: pointer;
            touch-action: manipulation;
            display: flex;
            align-items: center;
            justify-content: center;
            -webkit-tap-highlight-color: transparent;
        }
        .control-button:active {
            background: rgba(255, 255, 255, 0.5);
        }
        .boost-button {
            position: fixed;
            bottom: 20px;
            right: 220px;
            width: 80px;
            height: 80px;
            border: none;
            border-radius: 50%;
            background: rgba(255, 107, 107, 0.5);
            color: white;
            font-size: 16px;
            cursor: pointer;
            touch-action: manipulation;
            display: flex;
            align-items: center;
            justify-content: center;
            -webkit-tap-highlight-color: transparent;
        }
        .boost-button:active {
            background: rgba(255, 107, 107, 0.7);
        }
        @media (max-width: 768px) {
            #controls {
                display: none;
            }
        }
    </style>
    <script type="importmap">
        {
            "imports": {
                "three": "https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.module.js",
                "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.158.0/examples/jsm/"
            }
        }
    </script>
</head>
<body>
    <div id="info">笨牛小鱼</div>
    <div id="controls">
        控制方式：<br>
        ↑/W: 向上<br>
        ↓/S: 向下<br>
        ←/A: 向左<br>
        →/D: 向右<br>
        空格: 加速
    </div>
    <div class="control-buttons">
        <button class="control-button" id="up-left">↖</button>
        <button class="control-button" id="up">↑</button>
        <button class="control-button" id="up-right">↗</button>
        <button class="control-button" id="left">←</button>
        <button class="control-button" style="visibility: hidden;"></button>
        <button class="control-button" id="right">→</button>
        <button class="control-button" id="down-left">↙</button>
        <button class="control-button" id="down">↓</button>
        <button class="control-button" id="down-right">↘</button>
    </div>
    <button class="boost-button" id="boost">加速</button>
    <script type="module">
        import * as THREE from 'three';
        import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
        import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
        import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

        class Fish {
            constructor() {
                this.bodyGeometry = new THREE.Group();

                // Create fish body using custom shape
                const bodyShape = new THREE.Shape();
                // Start from the nose
                bodyShape.moveTo(0, 0);
                // Top curve
                bodyShape.bezierCurveTo(
                    1, 0.5,  // control point 1
                    2, 0.5,  // control point 2
                    3, 0     // end point
                );
                // Bottom curve
                bodyShape.bezierCurveTo(
                    2, -0.5, // control point 1
                    1, -0.5, // control point 2
                    0, 0     // back to start
                );

                const extrudeSettings = {
                    steps: 1,
                    depth: 0.6,
                    bevelEnabled: true,
                    bevelThickness: 0.2,
                    bevelSize: 0.2,
                    bevelSegments: 3
                };

                const bodyGeometry = new THREE.ExtrudeGeometry(bodyShape, extrudeSettings);
                const bodyMaterial = new THREE.MeshPhongMaterial({
                    color: 0x98ff98,
                    shininess: 100,
                    side: THREE.DoubleSide
                });
                this.body = new THREE.Mesh(bodyGeometry, bodyMaterial);
                this.body.scale.set(0.3, 0.3, 0.3);
                this.bodyGeometry.add(this.body);

                // Create tail fin
                const tailShape = new THREE.Shape();
                tailShape.moveTo(0, 0);
                tailShape.bezierCurveTo(
                    0.5, 1,    // control point 1
                    1.5, 1,    // control point 2
                    2, 0       // end point
                );
                tailShape.bezierCurveTo(
                    1.5, -1,   // control point 1
                    0.5, -1,   // control point 2
                    0, 0       // back to start
                );

                const tailGeometry = new THREE.ShapeGeometry(tailShape);
                const tailMaterial = new THREE.MeshPhongMaterial({
                    color: 0x98ff98,
                    transparent: true,
                    opacity: 0.9,
                    side: THREE.DoubleSide
                });
                this.tail = new THREE.Mesh(tailGeometry, tailMaterial);
                this.tail.position.set(0.9, 0, 0);
                this.tail.scale.set(0.3, 0.3, 0.3);
                this.bodyGeometry.add(this.tail);

                // Create dorsal fin
                const dorsalShape = new THREE.Shape();
                dorsalShape.moveTo(0, 0);
                dorsalShape.bezierCurveTo(
                    0.3, 0.8,  // control point 1
                    0.6, 0.8,  // control point 2
                    0.9, 0     // end point
                );
                dorsalShape.lineTo(0, 0);

                const dorsalGeometry = new THREE.ShapeGeometry(dorsalShape);
                const finMaterial = new THREE.MeshPhongMaterial({
                    color: 0x98ff98,
                    transparent: true,
                    opacity: 0.8,
                    side: THREE.DoubleSide
                });
                this.dorsalFin = new THREE.Mesh(dorsalGeometry, finMaterial);
                this.dorsalFin.position.set(0.3, 0.3, 0);
                this.dorsalFin.scale.set(0.3, 0.3, 0.3);
                this.bodyGeometry.add(this.dorsalFin);

                // Create pectoral fins
                const pectoralShape = new THREE.Shape();
                pectoralShape.moveTo(0, 0);
                pectoralShape.bezierCurveTo(
                    0.3, 0.4,  // control point 1
                    0.6, 0.4,  // control point 2
                    0.9, 0     // end point
                );
                pectoralShape.bezierCurveTo(
                    0.6, -0.2, // control point 1
                    0.3, -0.2, // control point 2
                    0, 0       // back to start
                );

                const pectoralGeometry = new THREE.ShapeGeometry(pectoralShape);

                // Left pectoral fin
                this.leftPectoralFin = new THREE.Mesh(pectoralGeometry, finMaterial);
                this.leftPectoralFin.position.set(0.2, 0, 0.2);
                this.leftPectoralFin.scale.set(0.3, 0.3, 0.3);
                this.leftPectoralFin.rotation.y = Math.PI / 6;
                this.bodyGeometry.add(this.leftPectoralFin);

                // Right pectoral fin
                this.rightPectoralFin = new THREE.Mesh(pectoralGeometry, finMaterial);
                this.rightPectoralFin.position.set(0.2, 0, -0.2);
                this.rightPectoralFin.scale.set(0.3, 0.3, 0.3);
                this.rightPectoralFin.rotation.y = -Math.PI / 6;
                this.bodyGeometry.add(this.rightPectoralFin);

                // Create eyes
                const eyeGeometry = new THREE.SphereGeometry(0.1, 32, 32);
                const eyeMaterial = new THREE.MeshPhongMaterial({
                    color: 0xffffff,
                    shininess: 100
                });
                const pupilMaterial = new THREE.MeshPhongMaterial({
                    color: 0x000000,
                    shininess: 100
                });

                // Left eye
                this.leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
                this.leftEye.position.set(0, 0.15, 0.15);
                this.leftEye.scale.set(0.2, 0.2, 0.1);
                this.bodyGeometry.add(this.leftEye);

                const leftPupil = new THREE.Mesh(new THREE.SphereGeometry(0.05, 32, 32), pupilMaterial);
                leftPupil.position.set(0.02, 0.15, 0.18);
                this.bodyGeometry.add(leftPupil);

                // Right eye
                this.rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
                this.rightEye.position.set(0, 0.15, -0.15);
                this.rightEye.scale.set(0.2, 0.2, 0.1);
                this.bodyGeometry.add(this.rightEye);

                const rightPupil = new THREE.Mesh(new THREE.SphereGeometry(0.05, 32, 32), pupilMaterial);
                rightPupil.position.set(0.02, 0.15, -0.18);
                this.bodyGeometry.add(rightPupil);

                // Create mouth
                const mouthGeometry = new THREE.TorusGeometry(0.1, 0.02, 16, 32, Math.PI);
                const mouthMaterial = new THREE.MeshPhongMaterial({ color: 0x000000 });
                this.mouth = new THREE.Mesh(mouthGeometry, mouthMaterial);
                this.mouth.position.set(0, -0.1, 0);
                this.mouth.rotation.x = Math.PI / 2;
                this.bodyGeometry.add(this.mouth);

                // Create text
                const canvas = document.createElement('canvas');
                canvas.width = 512;
                canvas.height = 256;
                const context = canvas.getContext('2d');

                // Create gradient for text
                const gradient = context.createLinearGradient(0, 0, canvas.width, 0);
                gradient.addColorStop(0, '#006400');
                gradient.addColorStop(0.5, '#98ff98');
                gradient.addColorStop(1, '#006400');

                context.fillStyle = gradient;
                context.font = 'bold 80px Arial';
                context.textAlign = 'center';
                context.textBaseline = 'middle';
                context.fillText('笨小鱼', canvas.width / 2, canvas.height / 2);

                const textTexture = new THREE.CanvasTexture(canvas);
                const textMaterial = new THREE.MeshBasicMaterial({
                    map: textTexture,
                    transparent: true,
                    side: THREE.DoubleSide
                });

                const textGeometry = new THREE.PlaneGeometry(1, 0.5);
                this.text = new THREE.Mesh(textGeometry, textMaterial);
                this.text.position.set(0, 0.5, 0);
                this.bodyGeometry.add(this.text);

                // Add to scene and set initial position
                scene.add(this.bodyGeometry);

                // Animation parameters
                this.velocity = new THREE.Vector3();
                this.acceleration = new THREE.Vector3();
                this.maxSpeed = 0.05;
                this.friction = 0.98;
                this.isControlled = true;
                this.targetRotation = new THREE.Euler();
                this.rotationSpeed = 0.1;
                this.isBoosting = false;

                // Initial position and rotation
                this.bodyGeometry.position.set(0, 0, 0);
                this.bodyGeometry.rotation.y = Math.PI;

                console.log('Fish created at position:', this.bodyGeometry.position);
            }

            applyForce(force) {
                this.acceleration.add(force);
            }

            update(deltaTime) {
                if (this.isControlled) {
                    // Apply acceleration and velocity
                    this.velocity.add(this.acceleration);
                    this.velocity.multiplyScalar(this.friction);

                    // Apply speed limit
                    const maxSpeed = this.isBoosting ? this.maxSpeed * 2 : this.maxSpeed;
                    if (this.velocity.length() > maxSpeed) {
                        this.velocity.normalize();
                        this.velocity.multiplyScalar(maxSpeed);
                    }

                    // Update position
                    this.bodyGeometry.position.add(this.velocity);

                    // Keep within bounds
                    const bounds = 8;
                    this.bodyGeometry.position.x = Math.max(-bounds, Math.min(bounds, this.bodyGeometry.position.x));
                    this.bodyGeometry.position.y = Math.max(-bounds/2, Math.min(bounds/2, this.bodyGeometry.position.y));
                    this.bodyGeometry.position.z = Math.max(-bounds, Math.min(bounds, this.bodyGeometry.position.z));

                    // Reset acceleration
                    this.acceleration.set(0, 0, 0);

                    // Update rotation to face movement direction
                    if (this.velocity.length() > 0.01) {
                        const targetRotation = Math.atan2(this.velocity.x, this.velocity.z);
                        const currentRotation = this.bodyGeometry.rotation.y;
                        let rotationDiff = targetRotation - currentRotation;

                        // Normalize rotation difference to [-PI, PI]
                        while (rotationDiff > Math.PI) rotationDiff -= Math.PI * 2;
                        while (rotationDiff < -Math.PI) rotationDiff += Math.PI * 2;

                        // Smooth rotation
                        this.bodyGeometry.rotation.y += rotationDiff * this.rotationSpeed;

                        // Tilt based on vertical movement
                        this.bodyGeometry.rotation.x = this.velocity.y * 0.5;
                    }

                    // Animate tail
                    const speed = this.velocity.length();
                    const tailAmplitude = Math.min(0.5, speed * 5);
                    this.tail.rotation.y = Math.sin(Date.now() * 0.01) * tailAmplitude;

                    // Update text to face camera
                    if (this.text) {
                        this.text.rotation.y = -this.bodyGeometry.rotation.y;
                    }
                }
            }
        }

        // Scene setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x87CEEB); // Sky blue background

        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 2, 5);

        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        document.body.appendChild(renderer.domElement);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(5, 5, 5);
        scene.add(directionalLight);

        // Water environment
        const waterGeometry = new THREE.PlaneGeometry(20, 20);
        const waterMaterial = new THREE.MeshStandardMaterial({
            color: 0x0099ff,
            transparent: true,
            opacity: 0.6
        });
        const water = new THREE.Mesh(waterGeometry, waterMaterial);
        water.rotation.x = -Math.PI / 2;
        water.position.y = -2;
        scene.add(water);

        // Controls
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.target.set(0, 0, 0);

        // Create fish instance
        const fish = new Fish();
        console.log('Initial fish position:', fish.bodyGeometry.position);

        // Keyboard controls
        const keys = {
            ArrowUp: false,
            ArrowDown: false,
            ArrowLeft: false,
            ArrowRight: false,
            w: false,
            s: false,
            a: false,
            d: false,
            ' ': false
        };

        window.addEventListener('keydown', (e) => {
            if (keys.hasOwnProperty(e.key)) {
                keys[e.key] = true;
            }
        });

        window.addEventListener('keyup', (e) => {
            if (keys.hasOwnProperty(e.key)) {
                keys[e.key] = false;
            }
        });

        // Touch controls
        const buttons = {
            'up': false,
            'down': false,
            'left': false,
            'right': false,
            'up-left': false,
            'up-right': false,
            'down-left': false,
            'down-right': false,
            'boost': false
        };

        function handleButtonPress(buttonId, isPressed) {
            buttons[buttonId] = isPressed;
            updateMovementFromButtons();
        }

        function updateMovementFromButtons() {
            const force = new THREE.Vector3();
            const moveSpeed = 0.005;

            if (buttons['up'] || buttons['up-left'] || buttons['up-right']) force.z -= moveSpeed;
            if (buttons['down'] || buttons['down-left'] || buttons['down-right']) force.z += moveSpeed;
            if (buttons['left'] || buttons['up-left'] || buttons['down-left']) force.x -= moveSpeed;
            if (buttons['right'] || buttons['up-right'] || buttons['down-right']) force.x += moveSpeed;

            fish.isBoosting = keys[' '] || buttons['boost'];
            fish.applyForce(force);
        }

        // Add touch event listeners
        Object.keys(buttons).forEach(buttonId => {
            const button = document.getElementById(buttonId);
            if (button) {
                button.addEventListener('touchstart', (e) => {
                    e.preventDefault();
                    handleButtonPress(buttonId, true);
                });
                button.addEventListener('touchend', (e) => {
                    e.preventDefault();
                    handleButtonPress(buttonId, false);
                });
                button.addEventListener('mousedown', () => handleButtonPress(buttonId, true));
                button.addEventListener('mouseup', () => handleButtonPress(buttonId, false));
                button.addEventListener('mouseleave', () => handleButtonPress(buttonId, false));
            }
        });

        // Update fish movement function
        function updateFishMovement() {
            const force = new THREE.Vector3();
            const moveSpeed = 0.005;

            // Keyboard controls
            if (keys.ArrowUp || keys.w) force.z -= moveSpeed;
            if (keys.ArrowDown || keys.s) force.z += moveSpeed;
            if (keys.ArrowLeft || keys.a) force.x -= moveSpeed;
            if (keys.ArrowRight || keys.d) force.x += moveSpeed;

            // Touch controls
            if (buttons['up'] || buttons['up-left'] || buttons['up-right']) force.z -= moveSpeed;
            if (buttons['down'] || buttons['down-left'] || buttons['down-right']) force.z += moveSpeed;
            if (buttons['left'] || buttons['up-left'] || buttons['down-left']) force.x -= moveSpeed;
            if (buttons['right'] || buttons['up-right'] || buttons['down-right']) force.x += moveSpeed;

            fish.isBoosting = keys[' '] || buttons['boost'];

            if (force.length() > 0) {
                force.normalize().multiplyScalar(moveSpeed);
                fish.applyForce(force);
            }
        }

        // Animation loop
        const clock = new THREE.Clock();
        function animate() {
            requestAnimationFrame(animate);

            const deltaTime = clock.getDelta();

            // Update fish movement based on input
            updateFishMovement();

            // Update fish animation
            fish.update(deltaTime);

            // Update camera to follow fish
            const cameraOffset = new THREE.Vector3(0, 2, 5);
            camera.position.copy(fish.bodyGeometry.position).add(cameraOffset);
            controls.target.copy(fish.bodyGeometry.position);

            controls.update();
            renderer.render(scene, camera);
        }

        animate();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
