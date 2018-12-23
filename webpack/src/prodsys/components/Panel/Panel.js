import RavenBoundary from 'common/components/RavenBoundary'
import cx from 'classnames'

const TopBar = ({ children }) => <nav className="TopBar">{children}</nav>
const BottomBar = ({ children }) => <nav className="BottomBar">{children}</nav>

const Panel = ({
  children,
  header = null,
  footer = null,
  className,
  scroll = true,
  ...props
}) => (
  <section className={cx('Panel', className)} {...props}>
    <RavenBoundary>
      {header && <TopBar>{header}</TopBar>}
      <RavenBoundary>
        <section className={cx('content', { scroll })}>{children}</section>
      </RavenBoundary>
      {footer && <BottomBar>{footer}</BottomBar>}
    </RavenBoundary>
  </section>
)
export default Panel
