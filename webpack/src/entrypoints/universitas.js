// frontpage of universitas.no react app
import 'babel-polyfill'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import ProdSys from './ProdSys'

const ROOT_ID = 'ReactApp'
const DOMNode = document.getElementById(ROOT_ID)

const render = () => {
  ReactDOM.render(
    <AppContainer>
      <ProdSys />
    </AppContainer>,
    DOMNode
  )
}

if (DOMNode) {
  render()
  module.hot && module.hot.accept('./Universitas', render)
} else {
  console.error(`Could not mount React App, because  #${ROOT_ID} was not found`)
}
