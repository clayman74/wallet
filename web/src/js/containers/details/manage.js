/* eslint camelcase: 0 */

import React from 'react';
import { connect } from 'react-redux';
import { push } from 'react-router-redux';

import { createDetail, getDetail, editDetail, removeDetail } from '../../actions/details';

import ManagePage from '../common/manage';
import Page from '../../components/common/page';
import ManageForm from '../../components/details/manage';


class ManageDetail extends ManagePage {
    constructor(props) {
        super(props);

        const transactionID = this.getTransactionID();

        this.doneRedirect = `/transactions/${transactionID}/details`;
        this.leftLinkPath = `/transactions/${transactionID}/details`;
    }

    componentWillMount() {
        const instanceID = this.getInstanceID();
        if (instanceID) {
            this.props.getAction({
                id: instanceID,
                transaction_id: this.getTransactionID()
            });
        }
    }

    handleSubmit(instance, payload) {
        const transactionID = this.getTransactionID();

        if (Object.keys(instance).length) {
            this.props.editAction(instance, payload);
        } else {
            this.props.createAction({ id: transactionID }, payload);
        }
    }

    getTransactionID() {
        const { transactionID } = this.props.routeParams;
        return typeof transactionID !== 'undefined' ? parseInt(transactionID, 10) : 0;
    }

    render() {
        const instanceID = this.getInstanceID();
        let instance = this.getInstance();

        let title = 'Add detail';
        let rightButton = {};
        if (instanceID) {
            title = 'Edit detail';
            rightButton = this.getRightLink(instance);
        }

        return (
            <Page title={title} leftButton={this.getLeftLink()} rightButton={rightButton} >
                <ManageForm
                    collection={this.props.collection}
                    instance={instance}
                    submitHandler={this.handleSubmit.bind(this, instance)}
                />
            </Page>
        );
    }
}

ManageDetail.propTypes = {
    // Props from Store
    collection: React.PropTypes.object.isRequired,
    routerState: React.PropTypes.object.isRequired,

    // Action creators
    pushState: React.PropTypes.func.isRequired,
    createAction: React.PropTypes.func.isRequired,
    getAction: React.PropTypes.func.isRequired,
    editAction: React.PropTypes.func.isRequired,
    removeAction: React.PropTypes.func.isRequired
};

function mapStateToProps(state) {
    return {
        collection: state.details,
        routerState: state.router
    };
}

const mapDispatchToProps = {
    pushState: push,
    createAction: createDetail,
    getAction: getDetail,
    editAction: editDetail,
    removeAction: removeDetail
};

export default connect(mapStateToProps, mapDispatchToProps)(ManageDetail);
