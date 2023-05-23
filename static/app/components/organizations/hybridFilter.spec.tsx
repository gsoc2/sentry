import {fireEvent, render, screen, userEvent} from 'sentry-test/reactTestingLibrary';

import {HybridFilter} from 'sentry/components/organizations/hybridFilter';

const props = {
  searchable: true,
  multiple: true,
  options: [
    {value: 'one', label: 'Option One'},
    {value: 'two', label: 'Option Two'},
    {value: 'three', label: 'Option Three'},
  ],
};

describe('ProjectPageFilter', function () {
  it('renders', async function () {
    render(<HybridFilter {...props} value={[]} onChange={() => {}} />);

    // Open menu, search input & all the options are there
    await userEvent.click(screen.getByRole('button', {expanded: false}));
    expect(screen.getByPlaceholderText('Search…')).toBeInTheDocument();
    expect(screen.getByRole('row', {name: 'Option One'})).toBeInTheDocument();
    expect(screen.getByRole('row', {name: 'Option Two'})).toBeInTheDocument();
    expect(screen.getByRole('row', {name: 'Option Three'})).toBeInTheDocument();
  });

  it('handles both single and multiple selection', async function () {
    const onChange = jest.fn();
    const {rerender} = render(<HybridFilter {...props} value={[]} onChange={onChange} />);

    // Clicking on Option One selects it (single selection)
    await userEvent.click(screen.getByRole('button', {expanded: false}));
    await userEvent.click(screen.getByRole('row', {name: 'Option One'}));
    expect(onChange).toHaveBeenCalledWith(['one']);
    expect(screen.getByRole('button', {expanded: false})).toBeInTheDocument();

    // HybridFilter is controlled-only, so we need to rerender it with new value
    rerender(<HybridFilter {...props} value={['one']} onChange={onChange} />);

    // Clicking on Option Two selects it and removes Option One from the selection state
    // (single selection mode)
    await userEvent.click(screen.getByRole('button', {expanded: false}));
    await userEvent.click(screen.getByRole('row', {name: 'Option Two'}));
    expect(onChange).toHaveBeenCalledWith(['two']);
  });

  it('handles multiple selection', async function () {
    const onChange = jest.fn();
    const {rerender} = render(<HybridFilter {...props} value={[]} onChange={onChange} />);

    // Clicking on the checkboxes in Option One & Option Two _adds_ the options to the
    // current selection state (multiple selection mode)
    await userEvent.click(screen.getByRole('button', {expanded: false}));
    await fireEvent.click(screen.getByRole('checkbox', {name: 'Select Option One'}));
    await fireEvent.click(screen.getByRole('checkbox', {name: 'Select Option Two'}));
    expect(screen.getByRole('checkbox', {name: 'Select Option One'})).toBeChecked();
    expect(screen.getByRole('checkbox', {name: 'Select Option Two'})).toBeChecked();

    // Clicking "Apply" commits the selection
    await userEvent.click(screen.getByRole('button', {name: 'Apply'}));
    expect(onChange).toHaveBeenCalledWith(expect.arrayContaining(['one', 'two']));

    // HybridFilter is controlled-only, so we need to rerender it with new value
    rerender(<HybridFilter {...props} value={['one', 'two']} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', {expanded: false}));

    // Ctrl-clicking on Option One & Option Two _removes_ them to the current selection
    // state (multiple selection mode)
    const ctrlKeyOpts = {
      key: 'Control',
      code: 'ControlLeft',
      keyCode: 17,
      which: 17,
      ctrlKey: true,
    };
    await fireEvent.keyDown(screen.getByRole('grid'), ctrlKeyOpts); // Press & hold Ctrl
    await userEvent.click(screen.getByRole('row', {name: 'Option One'}));
    await fireEvent.click(screen.getByRole('row', {name: 'Option Two'}));
    await fireEvent.keyUp(screen.getByRole('grid'), ctrlKeyOpts); // Release Ctrl
    expect(screen.getByRole('checkbox', {name: 'Select Option One'})).not.toBeChecked();
    expect(screen.getByRole('checkbox', {name: 'Select Option Two'})).not.toBeChecked();

    // Clicking "Apply" commits the selection
    await userEvent.click(screen.getByRole('button', {name: 'Apply'}));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('can cancel', async function () {
    const onChange = jest.fn();
    render(<HybridFilter {...props} value={[]} onChange={onChange} />);

    // Open the menu, select Option One
    await userEvent.click(screen.getByRole('button', {expanded: false}));
    await fireEvent.click(screen.getByRole('checkbox', {name: 'Select Option One'}));

    // Press Cancel
    await userEvent.click(screen.getByRole('button', {name: 'Cancel'}));
    // Open menu again
    await userEvent.click(screen.getByRole('button', {expanded: false}));

    // Option One isn't selected, onChange was never called
    expect(screen.getByRole('checkbox', {name: 'Select Option One'})).not.toBeChecked();
    expect(onChange).not.toHaveBeenCalled();
  });

  it('supports keyboard navigation', async function () {
    const onChange = jest.fn();
    render(<HybridFilter {...props} value={[]} onChange={onChange} />);

    // Open the menu, Option One is focused
    await userEvent.click(screen.getByRole('button', {expanded: false}));
    expect(screen.getByRole('row', {name: 'Option One'})).toHaveFocus();

    // Press Arrow Right to move focus to the checkbox
    await userEvent.keyboard('{ArrowRight}');
    expect(screen.getByRole('checkbox', {name: 'Select Option One'})).toHaveFocus();

    // Activate the checkbox. In browsers, users can press Space when the checkbox is
    // focused to activate it. With RTL, however, onChange events aren't fired on Space
    // key press (https://github.com/testing-library/react-testing-library/issues/122),
    // so we'll have to simulate a click event instead.
    await fireEvent.click(screen.getByRole('checkbox', {name: 'Select Option One'}));
    expect(screen.getByRole('checkbox', {name: 'Select Option One'})).toBeChecked();

    // Click "Apply" button, onChange is called
    await userEvent.click(screen.getByRole('button', {name: 'Apply'}));
    expect(onChange).toHaveBeenCalledWith(['one']);
  });
});
