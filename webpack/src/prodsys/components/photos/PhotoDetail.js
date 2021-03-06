import DetailPanel from 'components/DetailPanel'
import { connect } from 'react-redux'
import { Field, selectors, actions, MODEL } from './model.js'
import { PhotoTools } from '.'

const PhotoDetail = ({ pk, action }) => (
  <DetailPanel pk={pk} model={MODEL} getTitle={photo => `${photo.filename}`}>
    {action == 'crop' ? (
      <React.Fragment>
        <Field
          pk={pk}
          name="crop_box"
          type="cropbox"
          previews={[0.5, 1, 2.5]}
          editable
        />
        <Field pk={pk} name="description" editable />
      </React.Fragment>
    ) : (
      <React.Fragment>
        <Field pk={pk} name="large" key={pk} />
        <Field pk={pk} name="description" editable />
        <div className="wrapForm">
          <Field pk={pk} name="contributor" editable key={pk} />
          <Field pk={pk} name="category" editable />
          <Field pk={pk} name="filename" />
          <Field pk={pk} name="original" />
          <Field pk={pk} name="usage" />
          <Field pk={pk} name="created" />
          <Field pk={pk} name="filesize" />
          <Field pk={pk} name="height" />
          <Field pk={pk} name="width" />
        </div>
      </React.Fragment>
    )}
  </DetailPanel>
)

export default PhotoDetail
