import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Alert from '../components/ui/Alert';
import Table from '../components/ui/Table';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import Typography from '../components/ui/Typography';
import Modal from '../components/ui/Modal';
import Tabs from '../components/ui/Tabs';
import Progress from '../components/ui/Progress';
import Avatar from '../components/ui/Avatar';
import Switch from '../components/ui/Switch';
import Divider from '../components/ui/Divider';
import Checkbox from '../components/ui/Checkbox';
import Radio from '../components/ui/Radio';
import { Check, X, AlertTriangle, Info, CheckCircle2, AlertCircle } from 'lucide-react';
import { useState } from 'react';

function StyleGuidePage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [tabValue, setTabValue] = useState('colors');
  const [switchValue, setSwitchValue] = useState(false);
  const [checkboxValue, setCheckboxValue] = useState(false);
  const [radioValue, setRadioValue] = useState('option1');

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <Typography.H1>Style Guide</Typography.H1>
          <Typography.Muted className="mt-2">
            Comprehensive component library and design system for RankCare
          </Typography.Muted>
        </div>

        <Tabs value={tabValue} onValueChange={setTabValue}>
          <Tabs.List>
            <Tabs.Trigger value="colors">Colors</Tabs.Trigger>
            <Tabs.Trigger value="typography">Typography</Tabs.Trigger>
            <Tabs.Trigger value="buttons">Buttons</Tabs.Trigger>
            <Tabs.Trigger value="forms">Forms</Tabs.Trigger>
            <Tabs.Trigger value="feedback">Feedback</Tabs.Trigger>
            <Tabs.Trigger value="data">Data Display</Tabs.Trigger>
            <Tabs.Trigger value="overlays">Overlays</Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="colors">
            <Card className="mt-6">
              <Card.Header>
                <Typography.H3>Color Palette</Typography.H3>
              </Card.Header>
              <Card.Body>
                <div className="space-y-8">
                  <div>
                    <Typography.H4 className="mb-4">Brand Colors</Typography.H4>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      {['50', '100', '200', '300', '400', '500', '600', '700', '800', '900'].map((shade) => (
                        <div key={shade} className="text-center">
                          <div className={`h-20 rounded-lg bg-brand-${shade} mb-2`} />
                          <Typography.BodySmall>brand-{shade}</Typography.BodySmall>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Semantic Colors</Typography.H4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center">
                        <div className="h-20 rounded-lg bg-success mb-2" />
                        <Typography.BodySmall>Success</Typography.BodySmall>
                      </div>
                      <div className="text-center">
                        <div className="h-20 rounded-lg bg-warning mb-2" />
                        <Typography.BodySmall>Warning</Typography.BodySmall>
                      </div>
                      <div className="text-center">
                        <div className="h-20 rounded-lg bg-danger mb-2" />
                        <Typography.BodySmall>Danger</Typography.BodySmall>
                      </div>
                      <div className="text-center">
                        <div className="h-20 rounded-lg bg-info mb-2" />
                        <Typography.BodySmall>Info</Typography.BodySmall>
                      </div>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Neutral Colors</Typography.H4>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      {['50', '100', '200', '300', '400', '500', '600', '700', '800', '900'].map((shade) => (
                        <div key={shade} className="text-center">
                          <div className={`h-20 rounded-lg bg-slate-${shade} mb-2`} />
                          <Typography.BodySmall>slate-{shade}</Typography.BodySmall>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Tabs.Content>

          <Tabs.Content value="typography">
            <Card className="mt-6">
              <Card.Header>
                <Typography.H3>Typography</Typography.H3>
              </Card.Header>
              <Card.Body>
                <div className="space-y-6">
                  <div>
                    <Typography.H1>Heading 1</Typography.H1>
                    <Typography.Muted>text-3xl font-bold text-slate-900 tracking-tight</Typography.Muted>
                  </div>
                  <div>
                    <Typography.H2>Heading 2</Typography.H2>
                    <Typography.Muted>text-2xl font-bold text-slate-900 tracking-tight</Typography.Muted>
                  </div>
                  <div>
                    <Typography.H3>Heading 3</Typography.H3>
                    <Typography.Muted>text-xl font-semibold text-slate-900</Typography.Muted>
                  </div>
                  <div>
                    <Typography.H4>Heading 4</Typography.H4>
                    <Typography.Muted>text-lg font-semibold text-slate-900</Typography.Muted>
                  </div>
                  <div>
                    <Typography.H5>Heading 5</Typography.H5>
                    <Typography.Muted>text-base font-semibold text-slate-900</Typography.Muted>
                  </div>
                  <div>
                    <Typography.H6>Heading 6</Typography.H6>
                    <Typography.Muted>text-sm font-semibold text-slate-900 uppercase tracking-wider</Typography.Muted>
                  </div>
                  <Divider />
                  <div>
                    <Typography.Body>Body text - text-sm text-slate-700</Typography.Body>
                  </div>
                  <div>
                    <Typography.BodySmall>Body small - text-xs text-slate-600</Typography.BodySmall>
                  </div>
                  <div>
                    <Typography.Muted>Muted text - text-sm text-slate-500</Typography.Muted>
                  </div>
                  <div>
                    <Typography.MutedSmall>Muted small - text-xs text-slate-400</Typography.MutedSmall>
                  </div>
                  <div>
                    <Typography.Link>Link text - text-sm font-medium text-brand-600 hover:text-brand-700</Typography.Link>
                  </div>
                  <div>
                    <Typography.Error>Error text - text-sm text-danger</Typography.Error>
                  </div>
                  <div>
                    <Typography.Success>Success text - text-sm text-success</Typography.Success>
                  </div>
                  <div>
                    <Typography.Warning>Warning text - text-sm text-warning</Typography.Warning>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Tabs.Content>

          <Tabs.Content value="buttons">
            <Card className="mt-6">
              <Card.Header>
                <Typography.H3>Buttons</Typography.H3>
              </Card.Header>
              <Card.Body>
                <div className="space-y-8">
                  <div>
                    <Typography.H4 className="mb-4">Variants</Typography.H4>
                    <div className="flex flex-wrap gap-4">
                      <Button variant="primary">Primary</Button>
                      <Button variant="secondary">Secondary</Button>
                      <Button variant="danger">Danger</Button>
                      <Button variant="ghost">Ghost</Button>
                      <Button variant="outline">Outline</Button>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Sizes</Typography.H4>
                    <div className="flex flex-wrap items-center gap-4">
                      <Button size="sm">Small</Button>
                      <Button size="md">Medium</Button>
                      <Button size="lg">Large</Button>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">States</Typography.H4>
                    <div className="flex flex-wrap gap-4">
                      <Button>Normal</Button>
                      <Button disabled>Disabled</Button>
                      <Button loading>Loading</Button>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">With Icons</Typography.H4>
                    <div className="flex flex-wrap gap-4">
                      <Button leftIcon={<Check className="h-4 w-4" />}>With Left Icon</Button>
                      <Button rightIcon={<X className="h-4 w-4" />}>With Right Icon</Button>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Full Width</Typography.H4>
                    <Button fullWidth>Full Width Button</Button>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Tabs.Content>

          <Tabs.Content value="forms">
            <Card className="mt-6">
              <Card.Header>
                <Typography.H3>Form Components</Typography.H3>
              </Card.Header>
              <Card.Body>
                <div className="space-y-8">
                  <div>
                    <Typography.H4 className="mb-4">Input Fields</Typography.H4>
                    <div className="space-y-4 max-w-md">
                      <Input label="Default Input" placeholder="Enter text..." />
                      <Input label="With Error" error="This field is required" placeholder="Enter text..." />
                      <Input label="With Hint" hint="This is a helper text" placeholder="Enter text..." />
                      <Input label="Disabled" disabled placeholder="Disabled input..." />
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Textarea</Typography.H4>
                    <div className="max-w-md">
                      <Input.Textarea label="Message" rows={4} placeholder="Enter your message..." />
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Select</Typography.H4>
                    <div className="max-w-md">
                      <Input.Select label="Choose option">
                        <option>Option 1</option>
                        <option>Option 2</option>
                        <option>Option 3</option>
                      </Input.Select>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Checkbox</Typography.H4>
                    <div className="space-y-4">
                      <Checkbox label="Accept terms and conditions" checked={checkboxValue} onChange={setCheckboxValue} />
                      <Checkbox label="Disabled checkbox" disabled />
                      <Checkbox label="Checkbox with error" error="Please accept the terms" />
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Radio Buttons</Typography.H4>
                    <Radio.Group name="radio-group" value={radioValue} onChange={setRadioValue}>
                      <Radio value="option1" label="Option 1" />
                      <Radio value="option2" label="Option 2" />
                      <Radio value="option3" label="Option 3" />
                    </Radio.Group>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Switch</Typography.H4>
                    <div className="space-y-4">
                      <Switch label="Enable notifications" checked={switchValue} onChange={setSwitchValue} />
                      <Switch label="Disabled switch" disabled />
                    </div>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Tabs.Content>

          <Tabs.Content value="feedback">
            <Card className="mt-6">
              <Card.Header>
                <Typography.H3>Feedback Components</Typography.H3>
              </Card.Header>
              <Card.Body>
                <div className="space-y-8">
                  <div>
                    <Typography.H4 className="mb-4">Alerts</Typography.H4>
                    <div className="space-y-4">
                      <Alert variant="success" title="Success" message="Your changes have been saved successfully." />
                      <Alert variant="warning" title="Warning" message="Please review your input before proceeding." />
                      <Alert variant="error" title="Error" message="Something went wrong. Please try again." />
                      <Alert variant="info" title="Info" message="This is an informational message." />
                      <Alert variant="plain" message="This is a plain alert without title." />
                      <Alert 
                        variant="success" 
                        message="Dismissible alert with close button" 
                        dismissible 
                        onDismiss={() => console.log('Alert dismissed')} 
                      />
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Badges</Typography.H4>
                    <div className="flex flex-wrap gap-4">
                      <Badge tone="primary">Primary</Badge>
                      <Badge tone="secondary">Secondary</Badge>
                      <Badge tone="success">Success</Badge>
                      <Badge tone="warning">Warning</Badge>
                      <Badge tone="danger">Danger</Badge>
                      <Badge tone="info">Info</Badge>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Badge Sizes</Typography.H4>
                    <div className="flex flex-wrap items-center gap-4">
                      <Badge tone="primary" size="sm">Small</Badge>
                      <Badge tone="primary" size="md">Medium</Badge>
                      <Badge tone="primary" size="lg">Large</Badge>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Progress</Typography.H4>
                    <div className="space-y-4 max-w-md">
                      <Progress value={25} showLabel />
                      <Progress value={50} variant="success" showLabel />
                      <Progress value={75} variant="warning" showLabel />
                      <Progress value={100} variant="danger" showLabel />
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Spinner</Typography.H4>
                    <div className="flex gap-4">
                      <Progress.Spinner size="sm" />
                      <Progress.Spinner size="md" />
                      <Progress.Spinner size="lg" />
                    </div>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Tabs.Content>

          <Tabs.Content value="data">
            <Card className="mt-6">
              <Card.Header>
                <Typography.H3>Data Display Components</Typography.H3>
              </Card.Header>
              <Card.Body>
                <div className="space-y-8">
                  <div>
                    <Typography.H4 className="mb-4">Cards</Typography.H4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card>
                        <Card.Header>
                          <Typography.H5>Card Header</Typography.H5>
                        </Card.Header>
                        <Card.Body>
                          <Typography.Body>Card body content goes here.</Typography.Body>
                        </Card.Body>
                        <Card.Footer>
                          <Button size="sm">Action</Button>
                        </Card.Footer>
                      </Card>
                      <Card shadow="elevated">
                        <Card.Body>
                          <Typography.H5>Elevated Card</Typography.H5>
                          <Typography.Muted className="mt-2">With elevated shadow</Typography.Muted>
                        </Card.Body>
                      </Card>
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Table</Typography.H4>
                    <Table>
                      <Table.Header>
                        <Table.Row>
                          <Table.HeaderCell>Name</Table.HeaderCell>
                          <Table.HeaderCell>Email</Table.HeaderCell>
                          <Table.HeaderCell>Status</Table.HeaderCell>
                          <Table.HeaderCell>Role</Table.HeaderCell>
                        </Table.Row>
                      </Table.Header>
                      <Table.Body>
                        <Table.Row>
                          <Table.Cell>John Doe</Table.Cell>
                          <Table.Cell>john@example.com</Table.Cell>
                          <Table.Cell><Badge tone="success">Active</Badge></Table.Cell>
                          <Table.Cell>Admin</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell>Jane Smith</Table.Cell>
                          <Table.Cell>jane@example.com</Table.Cell>
                          <Table.Cell><Badge tone="warning">Pending</Badge></Table.Cell>
                          <Table.Cell>User</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell>Bob Johnson</Table.Cell>
                          <Table.Cell>bob@example.com</Table.Cell>
                          <Table.Cell><Badge tone="danger">Inactive</Badge></Table.Cell>
                          <Table.Cell>User</Table.Cell>
                        </Table.Row>
                      </Table.Body>
                    </Table>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Avatar</Typography.H4>
                    <div className="flex flex-wrap items-center gap-4">
                      <Avatar name="John Doe" size="sm" />
                      <Avatar name="Jane Smith" size="md" />
                      <Avatar name="Bob Johnson" size="lg" />
                      <Avatar name="Alice Williams" size="xl" />
                    </div>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Avatar Group</Typography.H4>
                    <Avatar.Group max={3}>
                      <Avatar name="John Doe" />
                      <Avatar name="Jane Smith" />
                      <Avatar name="Bob Johnson" />
                      <Avatar name="Alice Williams" />
                      <Avatar name="Charlie Brown" />
                    </Avatar.Group>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Divider</Typography.H4>
                    <div className="space-y-4">
                      <Divider />
                      <Divider label="With Label" />
                      <Divider variant="dashed" />
                    </div>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Tabs.Content>

          <Tabs.Content value="overlays">
            <Card className="mt-6">
              <Card.Header>
                <Typography.H3>Overlay Components</Typography.H3>
              </Card.Header>
              <Card.Body>
                <div className="space-y-8">
                  <div>
                    <Typography.H4 className="mb-4">Modal</Typography.H4>
                    <Button onClick={() => setModalOpen(true)}>Open Modal</Button>
                    <Modal
                      open={modalOpen}
                      onClose={() => setModalOpen(false)}
                      title="Example Modal"
                      size="md"
                      footer={
                        <>
                          <Button variant="outline" onClick={() => setModalOpen(false)}>
                            Cancel
                          </Button>
                          <Button onClick={() => setModalOpen(false)}>
                            Confirm
                          </Button>
                        </>
                      }
                    >
                      <Typography.Body>
                        This is an example modal dialog. It supports keyboard navigation (ESC to close)
                        and click outside to close.
                      </Typography.Body>
                    </Modal>
                  </div>

                  <div>
                    <Typography.H4 className="mb-4">Tabs</Typography.H4>
                    <Tabs defaultValue="tab1">
                      <Tabs.List>
                        <Tabs.Trigger value="tab1">Tab 1</Tabs.Trigger>
                        <Tabs.Trigger value="tab2">Tab 2</Tabs.Trigger>
                        <Tabs.Trigger value="tab3">Tab 3</Tabs.Trigger>
                      </Tabs.List>
                      <Tabs.Content value="tab1">
                        <Typography.Body>Content for Tab 1</Typography.Body>
                      </Tabs.Content>
                      <Tabs.Content value="tab2">
                        <Typography.Body>Content for Tab 2</Typography.Body>
                      </Tabs.Content>
                      <Tabs.Content value="tab3">
                        <Typography.Body>Content for Tab 3</Typography.Body>
                      </Tabs.Content>
                    </Tabs>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Tabs.Content>
        </Tabs>
      </div>
    </div>
  );
}

export default StyleGuidePage;
