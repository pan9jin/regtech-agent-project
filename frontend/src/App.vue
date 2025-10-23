<template>
  <div class="container">
    <!-- 헤더 -->
    <header class="header">
      <h1>🤖 RegTech Agent</h1>
      <p class="subtitle">AI 기반 규제 분석 및 워크플로우 자동화</p>
    </header>

    <!-- 네비게이션 탭 -->
    <nav class="tabs">
      <router-link
        to="/analyze"
        class="tab-btn"
        :class="{ active: currentRoute === 'analyze' }"
      >
        규제 분석
      </router-link>
      <router-link
        to="/results"
        class="tab-btn"
        :class="{ active: currentRoute === 'results' }"
      >
        분석 결과
      </router-link>
      <router-link
        to="/dashboard"
        class="tab-btn"
        :class="{ active: currentRoute === 'dashboard' }"
      >
        대시보드
      </router-link>
    </nav>

    <!-- 탭 컨텐츠 -->
    <div class="tab-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentRoute = computed(() => route.name)
</script>

<style>
/* 전역 스타일 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu',
    'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
  color: #333;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

/* 헤더 */
.header {
  text-align: center;
  color: white;
  margin-bottom: 30px;
  animation: fadeInDown 0.8s ease;
}

.header h1 {
  font-size: 2.5em;
  margin-bottom: 10px;
}

.subtitle {
  font-size: 1.1em;
  opacity: 0.9;
}

/* 탭 */
.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.tab-btn {
  flex: 1;
  padding: 15px 20px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  font-size: 1em;
  font-weight: 600;
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.3s ease;
  text-decoration: none;
  text-align: center;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.tab-btn.active {
  background: white;
  color: #667eea;
}

/* 탭 컨텐츠 */
.tab-content {
  animation: fadeIn 0.5s ease;
}

/* 애니메이션 */
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 반응형 */
@media (max-width: 768px) {
  body {
    padding: 10px;
  }

  .header h1 {
    font-size: 1.8em;
  }

  .subtitle {
    font-size: 0.95em;
  }

  .tabs {
    flex-direction: column;
  }
}
</style>
