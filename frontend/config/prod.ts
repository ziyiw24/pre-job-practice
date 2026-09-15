import type { UserConfigExport } from '@tarojs/cli'

export default {
  defineConstants: {
    API_BASE_URL: JSON.stringify(process.env.TARO_APP_API_BASE_URL || ''),
  },
  mini: {},
  h5: {},
} satisfies UserConfigExport<'webpack5'>
