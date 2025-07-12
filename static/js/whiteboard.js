class CollaborativeWhiteboard {
    constructor() {
        this.canvas = document.getElementById('whiteboard');
        this.ctx = this.canvas.getContext('2d');
        this.socket = null;
        this.isDrawing = false;
        this.currentTool = 'pen';
        this.currentColor = '#000000';
        this.currentSize = 5;
        this.currentOpacity = 1;
        this.zoom = 1;
        this.panOffset = { x: 0, y: 0 };
        this.isPanning = false;
        this.lastPanPoint = { x: 0, y: 0 };
        this.elements = [];
        this.history = [];
        this.historyStep = 0;
        this.participants = new Map();
        this.gridVisible = false;
        this.startPos = { x: 0, y: 0 };
        this.currentPath = [];
        
        this.init();
    }
    
    init() {
        this.setupCanvas();
        this.setupWebSocket();
        this.setupEventListeners();
        this.setupTouchEvents();
        this.resizeCanvas();
        
        // Handle window resize
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    setupCanvas() {
        this.canvas.style.background = 'white';
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.imageSmoothingEnabled = true;
    }
    
    setupWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/whiteboard/${window.ROOM_DATA.id}/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.updateParticipants();
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            setTimeout(() => {
                if (this.socket.readyState === WebSocket.CLOSED) {
                    this.setupWebSocket();
                }
            }, 3000);
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    setupEventListeners() {
        // Tool selection
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tool = e.currentTarget.dataset.tool;
                if (tool) {
                    this.setTool(tool);
                }
            });
        });
        
        // Color selection
        document.querySelectorAll('.color-option').forEach(option => {
            option.addEventListener('click', (e) => {
                this.setColor(e.currentTarget.dataset.color);
            });
        });
        
        // Custom color picker
        document.getElementById('custom-color').addEventListener('change', (e) => {
            this.setColor(e.target.value);
        });
        
        // Size control
        const sizeSlider = document.getElementById('brush-size');
        sizeSlider.addEventListener('input', (e) => {
            this.currentSize = parseInt(e.target.value);
            document.getElementById('size-display').textContent = `${this.currentSize}px`;
        });
        
        // Opacity control
        const opacitySlider = document.getElementById('opacity');
        opacitySlider.addEventListener('input', (e) => {
            this.currentOpacity = parseFloat(e.target.value);
            document.getElementById('opacity-display').textContent = `${Math.round(this.currentOpacity * 100)}%`;
        });
        
        // Action buttons
        document.getElementById('undo-btn').addEventListener('click', () => this.undo());
        document.getElementById('redo-btn').addEventListener('click', () => this.redo());
        document.getElementById('clear-btn').addEventListener('click', () => this.clearCanvas());
        document.getElementById('save-btn').addEventListener('click', () => this.saveSnapshot());
        document.getElementById('export-btn').addEventListener('click', () => this.exportImage());
        document.getElementById('grid-toggle').addEventListener('click', () => this.toggleGrid());
        
        // Zoom controls
        document.getElementById('zoom-in').addEventListener('click', () => this.zoomIn());
        document.getElementById('zoom-out').addEventListener('click', () => this.zoomOut());
        document.getElementById('zoom-reset').addEventListener('click', () => this.resetZoom());
        
        // Canvas events
        this.canvas.addEventListener('mousedown', (e) => this.handleStart(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleEnd(e));
        this.canvas.addEventListener('mouseleave', (e) => this.handleEnd(e));
        
        // Prevent context menu
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }
    
    setupTouchEvents() {
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousedown', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            this.canvas.dispatchEvent(mouseEvent);
        });
        
        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousemove', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            this.canvas.dispatchEvent(mouseEvent);
        });
        
        this.canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            const mouseEvent = new MouseEvent('mouseup', {});
            this.canvas.dispatchEvent(mouseEvent);
        });
    }
    
    resizeCanvas() {
        const container = this.canvas.parentElement;
        const rect = container.getBoundingClientRect();
        
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
        
        this.redrawCanvas();
    }
    
    getMousePos(e) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        
        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY
        };
    }
    
    setTool(tool) {
        // Remove active class from all tools
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Add active class to selected tool
        document.querySelector(`[data-tool="${tool}"]`).classList.add('active');
        
        this.currentTool = tool;
        this.canvas.className = `${tool}-tool`;
    }
    
    setColor(color) {
        // Remove active class from all color options
        document.querySelectorAll('.color-option').forEach(option => {
            option.classList.remove('active');
        });
        
        // Add active class to selected color
        const colorOption = document.querySelector(`[data-color="${color}"]`);
        if (colorOption) {
            colorOption.classList.add('active');
        }
        
        this.currentColor = color;
    }
    
    handleStart(e) {
        const pos = this.getMousePos(e);
        this.isDrawing = true;
        this.startPos = pos;
        
        if (this.currentTool === 'pan') {
            this.isPanning = true;
            this.lastPanPoint = pos;
            return;
        }
        
        if (this.currentTool === 'text') {
            this.showTextInput(pos);
            return;
        }
        
        this.currentPath = [pos];
        this.ctx.beginPath();
        this.ctx.moveTo(pos.x, pos.y);
        
        // Save state for undo/redo
        this.saveState();
    }
    
    handleMove(e) {
        const pos = this.getMousePos(e);
        
        // Send cursor position to other users
        this.sendCursorUpdate(pos);
        
        if (!this.isDrawing) return;
        
        if (this.currentTool === 'pan' && this.isPanning) {
            const dx = pos.x - this.lastPanPoint.x;
            const dy = pos.y - this.lastPanPoint.y;
            this.panOffset.x += dx;
            this.panOffset.y += dy;
            this.lastPanPoint = pos;
            this.redrawCanvas();
            return;
        }
        
        if (this.currentTool === 'pen' || this.currentTool === 'brush') {
            this.currentPath.push(pos);
            this.drawLine(this.currentPath[this.currentPath.length - 2], pos);
            
            // Send drawing data to other users
            this.sendDrawingData({
                type: 'draw',
                path: this.currentPath.slice(-2),
                color: this.currentColor,
                size: this.currentSize,
                opacity: this.currentOpacity,
                tool: this.currentTool
            });
        } else if (this.currentTool === 'eraser') {
            this.erase(pos);
        } else {
            // For shapes, redraw the preview
            this.redrawCanvas();
            this.drawShapePreview(this.startPos, pos);
        }
    }
    
    handleEnd(e) {
        if (!this.isDrawing) return;
        
        this.isDrawing = false;
        this.isPanning = false;
        
        const pos = this.getMousePos(e);
        
        if (this.currentTool === 'line' || this.currentTool === 'rectangle' || 
            this.currentTool === 'circle' || this.currentTool === 'arrow') {
            this.drawShape(this.startPos, pos);
            this.sendShapeData(this.startPos, pos);
        }
        
        if (this.currentPath.length > 0) {
            this.addElement({
                type: this.currentTool,
                path: this.currentPath,
                color: this.currentColor,
                size: this.currentSize,
                opacity: this.currentOpacity
            });
        }
        
        this.currentPath = [];
    }
    
    drawLine(from, to) {
        this.ctx.globalAlpha = this.currentOpacity;
        this.ctx.strokeStyle = this.currentColor;
        this.ctx.lineWidth = this.currentSize;
        
        this.ctx.beginPath();
        this.ctx.moveTo(from.x, from.y);
        this.ctx.lineTo(to.x, to.y);
        this.ctx.stroke();
        
        this.ctx.globalAlpha = 1;
    }
    
    drawShape(start, end) {
        this.ctx.globalAlpha = this.currentOpacity;
        this.ctx.strokeStyle = this.currentColor;
        this.ctx.lineWidth = this.currentSize;
        
        this.ctx.beginPath();
        
        switch (this.currentTool) {
            case 'line':
                this.ctx.moveTo(start.x, start.y);
                this.ctx.lineTo(end.x, end.y);
                break;
                
            case 'rectangle':
                const width = end.x - start.x;
                const height = end.y - start.y;
                this.ctx.rect(start.x, start.y, width, height);
                break;
                
            case 'circle':
                const radius = Math.sqrt(Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2));
                this.ctx.arc(start.x, start.y, radius, 0, 2 * Math.PI);
                break;
                
            case 'arrow':
                this.drawArrow(start, end);
                break;
        }
        
        this.ctx.stroke();
        this.ctx.globalAlpha = 1;
    }
    
    drawShapePreview(start, end) {
        this.ctx.globalAlpha = 0.5;
        this.ctx.strokeStyle = this.currentColor;
        this.ctx.lineWidth = this.currentSize;
        this.ctx.setLineDash([5, 5]);
        
        this.drawShape(start, end);
        
        this.ctx.setLineDash([]);
        this.ctx.globalAlpha = 1;
    }
    
    drawArrow(start, end) {
        const headLength = 20;
        const angle = Math.atan2(end.y - start.y, end.x - start.x);
        
        // Draw line
        this.ctx.moveTo(start.x, start.y);
        this.ctx.lineTo(end.x, end.y);
        
        // Draw arrowhead
        this.ctx.moveTo(end.x, end.y);
        this.ctx.lineTo(
            end.x - headLength * Math.cos(angle - Math.PI / 6),
            end.y - headLength * Math.sin(angle - Math.PI / 6)
        );
        this.ctx.moveTo(end.x, end.y);
        this.ctx.lineTo(
            end.x - headLength * Math.cos(angle + Math.PI / 6),
            end.y - headLength * Math.sin(angle + Math.PI / 6)
        );
    }
    
    erase(pos) {
        this.ctx.globalCompositeOperation = 'destination-out';
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, this.currentSize, 0, 2 * Math.PI);
        this.ctx.fill();
        this.ctx.globalCompositeOperation = 'source-over';
    }
    
    showTextInput(pos) {
        const textInput = document.getElementById('text-input');
        const input = textInput.querySelector('input');
        
        textInput.style.left = `${pos.x}px`;
        textInput.style.top = `${pos.y}px`;
        textInput.style.display = 'block';
        input.focus();
        
        const handleTextSubmit = () => {
            const text = input.value.trim();
            if (text) {
                this.drawText(text, pos);
                this.sendTextData(text, pos);
            }
            textInput.style.display = 'none';
            input.value = '';
            input.removeEventListener('keydown', handleKeydown);
        };
        
        const handleKeydown = (e) => {
            if (e.key === 'Enter') {
                handleTextSubmit();
            } else if (e.key === 'Escape') {
                textInput.style.display = 'none';
                input.value = '';
                input.removeEventListener('keydown', handleKeydown);
            }
        };
        
        input.addEventListener('keydown', handleKeydown);
    }
    
    drawText(text, pos) {
        this.ctx.globalAlpha = this.currentOpacity;
        this.ctx.fillStyle = this.currentColor;
        this.ctx.font = `${this.currentSize * 3}px Arial`;
        this.ctx.fillText(text, pos.x, pos.y);
        this.ctx.globalAlpha = 1;
    }
    
    drawGrid() {
        if (!this.gridVisible) return;
        
        const gridSize = 20;
        this.ctx.strokeStyle = '#e0e0e0';
        this.ctx.lineWidth = 1;
        this.ctx.globalAlpha = 0.5;
        
        for (let x = 0; x <= this.canvas.width; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        
        for (let y = 0; y <= this.canvas.height; y += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
        
        this.ctx.globalAlpha = 1;
    }
    
    toggleGrid() {
        this.gridVisible = !this.gridVisible;
        document.getElementById('grid-toggle').classList.toggle('active', this.gridVisible);
        this.redrawCanvas();
    }
    
    redrawCanvas() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawGrid();
        
        // Redraw all elements
        this.elements.forEach(element => {
            this.drawElement(element);
        });
    }
    
    drawElement(element) {
        this.ctx.globalAlpha = element.opacity || 1;
        this.ctx.strokeStyle = element.color;
        this.ctx.lineWidth = element.size;
        
        if (element.path && element.path.length > 1) {
            this.ctx.beginPath();
            this.ctx.moveTo(element.path[0].x, element.path[0].y);
            for (let i = 1; i < element.path.length; i++) {
                this.ctx.lineTo(element.path[i].x, element.path[i].y);
            }
            this.ctx.stroke();
        }
        
        this.ctx.globalAlpha = 1;
    }
    
    addElement(element) {
        this.elements.push(element);
    }
    
    saveState() {
        // Remove any states after current step
        this.history = this.history.slice(0, this.historyStep + 1);
        
        // Add current state
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        this.history.push(imageData);
        this.historyStep++;
        
        // Limit history size
        if (this.history.length > 50) {
            this.history.shift();
            this.historyStep--;
        }
    }
    
    undo() {
        if (this.historyStep > 0) {
            this.historyStep--;
            const imageData = this.history[this.historyStep];
            this.ctx.putImageData(imageData, 0, 0);
        }
    }
    
    redo() {
        if (this.historyStep < this.history.length - 1) {
            this.historyStep++;
            const imageData = this.history[this.historyStep];
            this.ctx.putImageData(imageData, 0, 0);
        }
    }
    
    clearCanvas() {
        if (confirm('Are you sure you want to clear the entire whiteboard?')) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.elements = [];
            this.sendMessage({ type: 'clear' });
            this.saveState();
        }
    }
    
    zoomIn() {
        this.zoom = Math.min(this.zoom * 1.2, 5);
        this.updateZoom();
    }
    
    zoomOut() {
        this.zoom = Math.max(this.zoom / 1.2, 0.2);
        this.updateZoom();
    }
    
    resetZoom() {
        this.zoom = 1;
        this.panOffset = { x: 0, y: 0 };
        this.updateZoom();
    }
    
    updateZoom() {
        this.canvas.style.transform = `scale(${this.zoom}) translate(${this.panOffset.x}px, ${this.panOffset.y}px)`;
        document.getElementById('zoom-display').textContent = `${Math.round(this.zoom * 100)}%`;
    }
    
    saveSnapshot() {
        const name = prompt('Enter snapshot name:');
        if (name) {
            // This would typically send to the server
            console.log('Saving snapshot:', name);
        }
    }
    
    exportImage() {
        const link = document.createElement('a');
        link.download = `whiteboard-${Date.now()}.png`;
        link.href = this.canvas.toDataURL();
        link.click();
    }
    
    handleKeyboard(e) {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'z':
                    e.preventDefault();
                    if (e.shiftKey) {
                        this.redo();
                    } else {
                        this.undo();
                    }
                    break;
                case 'y':
                    e.preventDefault();
                    this.redo();
                    break;
            }
        }
        
        // Tool shortcuts
        switch (e.key) {
            case 'p': this.setTool('pen'); break;
            case 'b': this.setTool('brush'); break;
            case 'e': this.setTool('eraser'); break;
            case 'l': this.setTool('line'); break;
            case 'r': this.setTool('rectangle'); break;
            case 'c': this.setTool('circle'); break;
            case 't': this.setTool('text'); break;
            case 's': this.setTool('select'); break;
        }
    }
    
    // WebSocket methods
    sendMessage(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        }
    }
    
    sendDrawingData(data) {
        this.sendMessage(data);
    }
    
    sendShapeData(start, end) {
        this.sendMessage({
            type: 'add_element',
            element_type: this.currentTool,
            x: start.x,
            y: start.y,
            width: end.x - start.x,
            height: end.y - start.y,
            color: this.currentColor,
            stroke_width: this.currentSize,
            opacity: this.currentOpacity
        });
    }
    
    sendTextData(text, pos) {
        this.sendMessage({
            type: 'add_element',
            element_type: 'text',
            x: pos.x,
            y: pos.y,
            text_content: text,
            color: this.currentColor,
            font_size: this.currentSize * 3
        });
    }
    
    sendCursorUpdate(pos) {
        this.sendMessage({
            type: 'cursor_move',
            x: pos.x,
            y: pos.y
        });
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'initial_state':
                this.loadInitialState(data.elements);
                break;
            case 'draw_update':
                this.handleRemoteDrawing(data);
                break;
            case 'element_added':
                this.handleRemoteElement(data);
                break;
            case 'cursor_update':
                this.updateRemoteCursor(data);
                break;
            case 'user_joined':
            case 'user_left':
                this.updateParticipants();
                break;
            case 'whiteboard_cleared':
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                this.elements = [];
                break;
        }
    }
    
    loadInitialState(elements) {
        this.elements = elements;
        this.redrawCanvas();
    }
    
    handleRemoteDrawing(data) {
        // Draw remote user's drawing
        const path = data.path_data ? JSON.parse(data.path_data) : data.path;
        if (path && path.length > 1) {
            this.ctx.globalAlpha = data.opacity || 1;
            this.ctx.strokeStyle = data.color;
            this.ctx.lineWidth = data.stroke_width || data.size;
            
            this.ctx.beginPath();
            this.ctx.moveTo(path[0].x, path[0].y);
            this.ctx.lineTo(path[1].x, path[1].y);
            this.ctx.stroke();
            
            this.ctx.globalAlpha = 1;
        }
    }
    
    handleRemoteElement(data) {
        // Handle remote shapes, text, etc.
        this.addElement({
            type: data.element_type,
            x: data.x,
            y: data.y,
            width: data.width,
            height: data.height,
            color: data.color,
            size: data.stroke_width,
            text: data.text_content
        });
        this.redrawCanvas();
    }
    
    updateRemoteCursor(data) {
        const cursors = document.querySelectorAll('.cursor');
        let cursor = document.querySelector(`[data-user="${data.user}"]`);
        
        if (!cursor) {
            cursor = document.createElement('div');
            cursor.className = 'cursor';
            cursor.dataset.user = data.user;
            cursor.dataset.username = data.user;
            cursor.innerHTML = '&#8594;'; // Arrow symbol
            document.querySelector('.canvas-container').appendChild(cursor);
        }
        
        cursor.style.left = `${data.x}px`;
        cursor.style.top = `${data.y}px`;
        cursor.style.color = data.color || '#007bff';
    }
    
    updateParticipants() {
        // This would typically fetch from server
        // For now, just update the UI
        const participantsList = document.getElementById('participants-list');
        // Implementation would fetch and display current participants
    }
}

// Initialize whiteboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CollaborativeWhiteboard();
});

