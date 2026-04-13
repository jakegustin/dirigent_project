package hierarchical

import (
    "context"

    v1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/kubernetes/pkg/scheduler/framework"
	fwk "k8s.io/kube-scheduler/framework"
)

const Name = "hierarchical_scheduler"

type HierarchicalPlugin struct {
    handle framework.Handle
}

var _ framework.ScorePlugin = &HierarchicalPlugin{}

func New(_ context.Context, _ runtime.Object, h framework.Handle) (framework.Plugin, error) {
    return &HierarchicalPlugin{handle: h}, nil
}

func (p *HierarchicalPlugin) Name() string { return Name }

func (p *HierarchicalPlugin) Score(ctx context.Context, state fwk.CycleState, pod *v1.Pod, nodeInfo fwk.NodeInfo) (int64, *fwk.Status) {
    allocatable := nodeInfo.GetAllocatable().GetMilliCPU()
    if allocatable == 0 {
        return 0, fwk.NewStatus(fwk.Error, "node has zero allocatable CPU")
    }

    requested := nodeInfo.GetRequested().GetMilliCPU()
    utilization := float64(requested) / float64(allocatable) * 100

    node := nodeInfo.Node()
    if node == nil {
        return 0, fwk.NewStatus(fwk.Error, "node not found in cache")
    }
    nodeClass := node.Labels["node-class"]

    switch nodeClass {
    case "fast":
        if utilization < 90 {
            return 100, nil
        }
        return 25, nil
    case "slow":
        if utilization < 90 {
            return 50, nil
        }
        return 10, nil
    default:
        return 0, nil
    }
}

func (p *HierarchicalPlugin) ScoreExtensions() framework.ScoreExtensions { return nil }