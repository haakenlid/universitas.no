import R from 'ramda'
import {
  takeLatest,
  takeEvery,
  select,
  call,
  put,
  all,
  fork,
  take,
} from 'redux-saga/effects'
import { delay } from 'redux-saga'
import { apiPatch, apiList, apiGet } from '../services/api'
import {
  issuesFetched,
  issueSelected,
  issuePatched,
  ITEMS_REQUESTED,
  ITEM_SELECTED,
  FILTER_TOGGLED,
  FIELD_CHANGED,
  getIssue,
  getQuery,
  issueAdded,
} from './duck'

export default function* rootSaga() {
  yield takeLatest(FILTER_TOGGLED, requestIssues)
  yield takeLatest(ITEM_SELECTED, selectIssue)
  yield takeLatest(FIELD_CHANGED, patchIssue)
  yield takeEvery(ITEMS_REQUESTED, requestIssues)
  yield fork(watchRouteChange)
}

const getModel = action => {
  return R.path(['payload', 'result', 'model'])(action)
}

function* watchRouteChange() {
  while (true) {
    const action = yield take('ROUTER_LOCATION_CHANGED')
    if (getModel(action) == 'issue') yield fork(requestIssues, action)
    const id = R.path(['payload', 'params', 'id'])(action)
    if (id) {
      yield put(issueSelected(parseInt(id)))
    } else {
      yield put(issueSelected(0))
    }
  }
}

function* selectIssue(action) {
  const id = action.payload.id
  let data = yield select(getIssue(id))
  if (id && !data) {
    data = yield call(apiGet('issues'), id)
    yield put(issueAdded(data.response))
  }
}
function* requestIssues(action) {
  console.log('request Issues')
  const data = yield call(fetchIssues)
  if (data) {
    yield put(issuesFetched(data))
  }
}
function* patchIssue(action) {
  // debounce
  yield call(delay, 500)
  const { id, field, value } = action.payload
  const data = yield call(apiPatch('issues'), id, { [field]: value })
  if (data) {
    yield put(issuePatched(data))
  }
}

function* fetchIssues() {
  const attrs = yield select(getQuery)
  const { response, error } = yield call(apiList, 'issues', attrs)
  if (response) {
    return response
  } else {
    yield put({ type: 'ERROR', error })
  }
}
