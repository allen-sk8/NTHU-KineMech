const { createApp } = Vue;

createApp({
    data() {
        return {
            folderPath: 'videos',
            videos: [],
            currentVideo: null,
            isPlaying: false,
            currentTime: 0,
            duration: 0,
            playbackRate: 1,
            templates: [],
            currentTemplateIndex: 0,
            annotations: [],
            showTemplateModal: false,
            editingTemplates: [],
            editingTemplateIndex: 0,
            toast: {
                visible: false,
                message: '',
                type: 'info',
                timeout: null
            }
        }
    },
    computed: {
        currentTags() {
            if (this.templates.length > 0 && this.templates[this.currentTemplateIndex]) {
                return this.templates[this.currentTemplateIndex].tags;
            }
            return [];
        },
        progressPercent() {
            if (!this.duration) return 0;
            return (this.currentTime / this.duration) * 100;
        },
        currentFrame() {
            if (!this.currentVideo) return 0;
            return Math.floor(this.currentTime * this.currentVideo.fps);
        },
        sortedAnnotations() {
            return [...this.annotations].sort((a, b) => a.timestamp_sec - b.timestamp_sec);
        },
        timelineSegments() {
            if (!this.duration || this.annotations.length === 0) return [];
            const sorted = [...this.annotations].sort((a, b) => a.timestamp_sec - b.timestamp_sec);
            const segments = [];
            let prevTime = 0;
            for (let i = 0; i < sorted.length; i++) {
                const ann = sorted[i];
                const startPct = (prevTime / this.duration) * 100;
                const endPct = (ann.timestamp_sec / this.duration) * 100;
                segments.push({
                    start: startPct,
                    width: Math.max(0, endPct - startPct),
                    color: this.getTagColor(ann.tag),
                    tag: ann.tag
                });
                prevTime = ann.timestamp_sec;
            }
            return segments;
        }
    },
    mounted() {
        this.loadTemplates();
        window.addEventListener('keydown', this.handleKeydown);
        this.loadVideos();
    },
    beforeUnmount() {
        window.removeEventListener('keydown', this.handleKeydown);
    },
    methods: {
        showToast(message, type = 'info') {
            this.toast.message = message;
            this.toast.type = type;
            this.toast.visible = true;
            
            if (this.toast.timeout) clearTimeout(this.toast.timeout);
            this.toast.timeout = setTimeout(() => {
                this.toast.visible = false;
            }, 3000);
        },
        async loadTemplates() {
            try {
                const res = await fetch('/api/templates');
                const data = await res.json();
                this.templates = data.templates;
            } catch (error) {
                console.error('Error loading templates:', error);
            }
        },
        async loadVideos() {
            if (!this.folderPath) return;
            try {
                const res = await fetch(`/api/videos?folder_path=${encodeURIComponent(this.folderPath)}`);
                if (!res.ok) throw new Error('目錄無效或讀取失敗');
                const data = await res.json();
                this.videos = data.videos;
                if (this.videos.length > 0) {
                    this.showToast(`成功載入 ${this.videos.length} 部影片`, 'success');
                }
            } catch (error) {
                console.warn(error.message);
            }
        },
        async selectVideo(video) {
            this.currentVideo = video;
            this.annotations = []; 
            
            const videoUrl = `/api/video_stream?path=${encodeURIComponent(video.path)}`;
            this.$refs.videoPlayer.src = videoUrl;
            this.$refs.videoPlayer.playbackRate = this.playbackRate;
            this.$refs.videoPlayer.load();
            
            try {
                const res = await fetch(`/api/annotations?folder_path=${encodeURIComponent(this.folderPath)}&filename=${encodeURIComponent(video.filename)}`);
                const data = await res.json();
                if (data.annotations && data.annotations.length > 0) {
                    this.annotations = data.annotations;
                }
            } catch (error) {
                console.error("No existing annotations found or error loading.");
            }
        },
        onVideoLoaded() {
            this.duration = this.$refs.videoPlayer.duration;
            this.isPlaying = !this.$refs.videoPlayer.paused;
        },
        onTimeUpdate() {
            this.currentTime = this.$refs.videoPlayer.currentTime;
        },
        togglePlay() {
            if (!this.currentVideo) return;
            if (this.$refs.videoPlayer.paused) {
                this.$refs.videoPlayer.play();
                this.isPlaying = true;
            } else {
                this.$refs.videoPlayer.pause();
                this.isPlaying = false;
            }
        },
        stepFrame(direction) {
            if (!this.currentVideo) return;
            this.$refs.videoPlayer.pause();
            this.isPlaying = false;
            
            const fps = this.currentVideo.fps || 30;
            const step = 1 / fps;
            this.$refs.videoPlayer.currentTime += (direction * step);
        },
        seekVideo(event) {
            if (!this.currentVideo) return;
            const rect = event.currentTarget.getBoundingClientRect();
            const pos = (event.clientX - rect.left) / rect.width;
            this.$refs.videoPlayer.currentTime = pos * this.duration;
        },
        updatePlaybackRate() {
            if (this.$refs.videoPlayer) {
                this.$refs.videoPlayer.playbackRate = parseFloat(this.playbackRate);
            }
        },
        formatTime(seconds) {
            if (isNaN(seconds)) return "00:00.00";
            const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
            const secs = Math.floor(seconds % 60).toString().padStart(2, '0');
            const ms = Math.floor((seconds % 1) * 100).toString().padStart(2, '0');
            return `${mins}:${secs}.${ms}`;
        },
        getTagColor(tagName) {
            let tag = this.currentTags.find(t => t.name === tagName);
            if (!tag) {
                for (let tpl of this.templates) {
                    tag = tpl.tags.find(t => t.name === tagName);
                    if (tag) break;
                }
            }
            return tag ? tag.color : '#9ca3af';
        },
        addAnnotation(tag) {
            if (!this.currentVideo) {
                this.showToast('請先載入並選擇影片', 'error');
                return;
            }
            
            const exists = this.annotations.some(a => a.tag === tag.name && Math.abs(a.timestamp_sec - this.currentTime) < 0.1);
            if (exists) return;
            
            this.annotations.push({
                tag: tag.name,
                timestamp_sec: this.currentTime,
                frame_index: this.currentFrame,
                shortcut: tag.shortcut
            });
        },
        removeAnnotation(index) {
            const target = this.sortedAnnotations[index];
            this.annotations = this.annotations.filter(a => a !== target);
        },
        jumpToAnnotation(ann) {
            if (!this.currentVideo || !this.$refs.videoPlayer) return;
            this.$refs.videoPlayer.currentTime = ann.timestamp_sec;
            this.$refs.videoPlayer.pause();
            this.isPlaying = false;
        },
        async saveAnnotations() {
            if (!this.currentVideo) return false;
            
            const payload = {
                video_filename: this.currentVideo.filename,
                fps: this.currentVideo.fps,
                annotations: this.annotations
            };
            
            try {
                const res = await fetch(`/api/annotations?folder_path=${encodeURIComponent(this.folderPath)}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (res.ok) {
                    this.showToast('標註已成功儲存', 'success');
                    return true;
                } else {
                    throw new Error('儲存失敗');
                }
            } catch (error) {
                this.showToast(error.message, 'error');
                return false;
            }
        },
        async saveAndNext() {
            if (!this.currentVideo) return;
            
            const success = await this.saveAnnotations();
            if (!success) return;
            
            this.currentVideo.is_annotated = true;
            
            const currentIndex = this.videos.findIndex(v => v.path === this.currentVideo.path);
            if (currentIndex !== -1 && currentIndex < this.videos.length - 1) {
                this.selectVideo(this.videos[currentIndex + 1]);
            } else {
                this.showToast('標註已儲存，這已經是最後一部影片了', 'success');
            }
        },
        openTemplateEditor() {
            this.editingTemplates = JSON.parse(JSON.stringify(this.templates));
            this.editingTemplateIndex = 0;
            this.showTemplateModal = true;
        },
        closeTemplateEditor() {
            this.showTemplateModal = false;
        },
        addEditingTemplate() {
            this.editingTemplates.push({
                name: '新範本',
                tags: []
            });
            this.editingTemplateIndex = this.editingTemplates.length - 1;
        },
        removeEditingTemplate(index) {
            this.editingTemplates.splice(index, 1);
            if (this.editingTemplateIndex >= this.editingTemplates.length) {
                this.editingTemplateIndex = Math.max(0, this.editingTemplates.length - 1);
            }
        },
        addTagToEditingTemplate() {
            if (this.editingTemplates[this.editingTemplateIndex]) {
                this.editingTemplates[this.editingTemplateIndex].tags.push({
                    name: '新標籤',
                    shortcut: '',
                    color: '#3b82f6'
                });
            }
        },
        removeTagFromEditingTemplate(tagIdx) {
            this.editingTemplates[this.editingTemplateIndex].tags.splice(tagIdx, 1);
        },
        async saveTemplatesToServer() {
            try {
                const res = await fetch('/api/templates', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ templates: this.editingTemplates })
                });
                if (res.ok) {
                    this.showToast('範本已儲存', 'success');
                    this.templates = JSON.parse(JSON.stringify(this.editingTemplates));
                    this.showTemplateModal = false;
                    if (this.currentTemplateIndex >= this.templates.length) {
                        this.currentTemplateIndex = Math.max(0, this.templates.length - 1);
                    }
                } else {
                    throw new Error('儲存範本失敗');
                }
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },
        handleKeydown(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
            if (this.showTemplateModal) return;
            
            if (e.code === 'Enter') {
                e.preventDefault();
                this.saveAndNext();
                return;
            }
            
            if (e.code === 'Space') {
                e.preventDefault();
                this.togglePlay();
                return;
            }
            
            if (e.code === 'ArrowLeft') {
                e.preventDefault();
                this.stepFrame(-1);
                return;
            }
            if (e.code === 'ArrowRight') {
                e.preventDefault();
                this.stepFrame(1);
                return;
            }
            
            const key = e.key.toLowerCase();
            const tag = this.currentTags.find(t => t.shortcut.toLowerCase() === key);
            if (tag) {
                e.preventDefault();
                this.addAnnotation(tag);
            }
        }
    }
}).mount('#app');
