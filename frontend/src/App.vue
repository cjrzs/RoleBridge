<template>
  <div id="app">
    <header>
      <h1>RoleBridge</h1>
      <p class="subtitle">跨职能沟通翻译助手</p>
    </header>
    <main>
      <div class="container">
        <TranslationInterface />
      </div>
    </main>
  </div>
</template>

<script>
import TranslationInterface from './components/TranslationInterface.vue'

export default {
  name: 'App',
  components: {
    TranslationInterface
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f5f5;
  color: #333;
  height: 100vh;
  overflow: hidden;
}

#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
}

main {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  min-height: 0;
}

.container {
  max-width: 95%;
  margin: 0 auto;
  width: 100%;
}
</style>

