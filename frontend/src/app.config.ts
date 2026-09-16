export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/generating/index',
    'pages/quiz/index',
    'pages/report/index',
    'pages/upload/index',
    'pages/review/index',
    'pages/manager/index',
    'pages/assignment/index',
    'pages/privacy/index',
    'pages/main/home/index',
    'pages/main/content/index',
    'pages/main/mine/index',
    'pages/onboarding/index',
    'pages/course/create/index',
  ],
  tabBar: {
    color: '#7b857f', selectedColor: '#174f3a', backgroundColor: '#ffffff', borderStyle: 'white',
    list: [
      { pagePath: 'pages/main/home/index', text: '首页', iconPath: 'assets/tab-home.png', selectedIconPath: 'assets/tab-home-active.png' },
      { pagePath: 'pages/main/content/index', text: '内容', iconPath: 'assets/tab-me.png', selectedIconPath: 'assets/tab-me-active.png' },
      { pagePath: 'pages/main/mine/index', text: '我的', iconPath: 'assets/tab-me.png', selectedIconPath: 'assets/tab-me-active.png' },
    ],
  },
  networkTimeout: {
    request: 600000,
    connectSocket: 600000,
    uploadFile: 600000,
    downloadFile: 600000,
  },
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: '上岗练',
    navigationBarTextStyle: 'black',
  },
})
