import { capitalize, phoneFormat } from 'utils/text'
import anonymous from 'images/anonymous.jpg'
import cx from 'classnames'
import './ContactCard.scss'

const Field = ({ name, label, value }) => (
  <div className={cx('Field', name)}>
    {label && <label className="label">{label}:</label>}
    <div className="value">{value}</div>
  </div>
)

const phoneLink = R.pipe(
  R.defaultTo(''),
  R.replace(/\s/g, ''),
  R.when(R.pipe(R.length, R.equals(8)), R.concat('+47')),
  R.concat('sms://'),
)

const phoneTo = R.ifElse(R.not, R.always('–'), phone => (
  <a href={phoneLink(phone)}>{phoneFormat(phone)}</a>
))

const mailTo = R.ifElse(R.not, R.always('–'), mail => (
  <a href={`mailto:${mail}`}>{R.replace(/@/, '\u200B@', mail)}</a>
))

export const ContactCard = ({
  id,
  position,
  display_name: name,
  phone,
  email,
  thumb = anonymous,
}) => (
  <div className="ContactCard">
    <img className="thumb" src={thumb} alt={name} />
    <Field
      name="position"
      label="stilling"
      value={capitalize(position.title)}
    />
    <Field name="name" label="" value={name} />
    <Field name="email" label="epost" value={mailTo(email)} />
    <Field name="phone" label="telefon" value={phoneTo(phone)} />
  </div>
)

export const ContactGrid = ({ contacts = [] }) => (
  <div className="ContactGrid">
    {contacts.map(props => <ContactCard key={props.id} {...props} />)}
  </div>
)
