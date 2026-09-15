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
  ],
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
